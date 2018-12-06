import psycopg2
import os
import sys
import logging as log
import time
import uuid
import argparse

from aws_requests_auth.aws_auth import AWSRequestsAuth
from elasticsearch import Elasticsearch, RequestsHttpConnection
from elasticsearch.exceptions import NotFoundError
from elasticsearch.exceptions \
    import ConnectionError as ElasticsearchConnectionError
from elasticsearch_dsl import Search, connections
from elasticsearch import helpers
from psycopg2.sql import SQL, Identifier
from es_syncer.elasticsearch_models import database_table_to_elasticsearch_model

"""
A daemon for synchronizing database with Elasticsearch. For each table to
sync, find its largest ID in database. Find the corresponding largest ID in
Elasticsearch. If the database ID is greater than the largest corresponding
ID in Elasticsearch, copy the missing records over to Elasticsearch.

Each table is database corresponds to an identically named index in
Elasticsearch. For instance, if database has a table that we would like to
replicate called 'image', the syncer will create an Elasticsearch called
'image' and populate the index with documents. See elasticsearch_models to 
change the format of Elasticsearch documents.

This is intended to be daemonized and run by a process supervisor.
"""

# For AWS IAM access to Elasticsearch
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL', 'localhost')
ELASTICSEARCH_PORT = int(os.environ.get('ELASTICSEARCH_PORT', 9200))
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

DATABASE_HOST = os.environ.get('DATABASE_HOST', 'localhost')
DATABASE_USER = os.environ.get('DATABASE_USER', 'deploy')
DATABASE_PASSWORD = os.environ.get('DATABASE_PASSWORD', 'deploy')
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'openledger')
DATABASE_PORT = int(os.environ.get('DATABASE_PORT', 5432))

# The number of database records to load in memory at once.
DB_BUFFER_SIZE = int(os.environ.get('DB_BUFFER_SIZE', 100000))

SYNCER_POLL_INTERVAL = int(os.environ.get('SYNCER_POLL_INTERVAL', 60))

# A comma separated list of tables in the database table to replicate to
# Elasticsearch. Ex: image,docs
REP_TABLES = os.environ.get('COPY_TABLES', 'image')
replicate_tables = REP_TABLES.split(',') if ',' in REP_TABLES else [REP_TABLES]


class ElasticsearchSyncer:

    def __init__(self, elasticsearch_instance, tables):
        self.es = elasticsearch_instance
        connections.connections.add_connection('default', self.es)
        self.tables_to_watch = tables

    @staticmethod
    def _get_last_item_ids(table):
        """
        Find the last item added to Postgres and return both its sequential ID
        and its UUID.
        :param table: The name of the database table to check.
        :return: A tuple containing a sequential ID and a UUID
        """

        pg_conn = database_connect()
        pg_conn.set_session(readonly=True)
        cur = pg_conn.cursor()
        # Find the last row added to the database table
        cur.execute(
            SQL(
                'SELECT id, identifier FROM {} ORDER BY id DESC LIMIT 1;'
            ).format(Identifier(table))
        )
        last_added_pg_id, last_added_uuid = cur.fetchone()
        cur.close()
        pg_conn.close()
        return last_added_pg_id, last_added_uuid

    def _synchronize(self, table, dest_idx=None):
        """
        Check that the database tables are in sync with Elasticsearch. If not,
        begin replication.
        """
        last_added_pg_id, _ = self._get_last_item_ids(table)
        if not last_added_pg_id:
            log.warning('Tried to sync ' + table + ' but it was empty.')
            return
        # Find the last document inserted into elasticsearch
        destination = dest_idx if dest_idx else table
        s = Search(using=self.es, index=destination)
        s.aggs.bucket('highest_pg_id', 'max', field='id')
        try:
            es_res = s.execute()
            last_added_es_id = \
                int(es_res.aggregations['highest_pg_id']['value'])
        except (TypeError, NotFoundError):
            log.info('No matching documents found in elasticsearch. '
                     'Replicating everything.')
            last_added_es_id = 0
        log.info(
            'highest_db_id, highest_es_id: {}, {}'
            .format(last_added_pg_id, last_added_es_id)
        )
        # Select all documents in-between and replicate to Elasticsearch.
        if last_added_pg_id > last_added_es_id:
            log.info('Replicating range ' + str(last_added_es_id) + '-' +
                     str(last_added_pg_id))
            self._replicate(last_added_es_id, last_added_pg_id, table, dest_idx)

    def _replicate(self, start, end, table, dest_index):
        """
        Replicate all of the records between `start` and `end`.

        :param start: The first ID to replicate
        :param end: The last ID to replicate
        :param table: The table to replicate this range from.
        :return:
        """
        cursor_name = table + '_table_cursor'
        # Enable writing to Postgres so we can create a server-side cursor.
        pg_conn = database_connect()
        with pg_conn.cursor(name=cursor_name) as server_cur:
            server_cur.itersize = DB_BUFFER_SIZE
            select_range = SQL(
                'SELECT * FROM {}'
                ' WHERE id BETWEEN %s AND %s ORDER BY id')\
                .format(Identifier(table))
            server_cur.execute(select_range, (start, end,))
            num_converted_documents = 0
            # Fetch a chunk and push it to Elasticsearch. Repeat until we run
            # out of chunks.
            while True:
                dl_start_time = time.time()
                chunk = server_cur.fetchmany(server_cur.itersize)
                dl_end_time = time.time() - dl_start_time
                dl_rate = len(chunk) / dl_end_time
                if not chunk:
                    break
                log.info(
                    'PSQL down: batch_size={}, downloaded_per_second={}'
                    .format(len(chunk), dl_rate)
                )
                es_batch = self.pg_chunk_to_es(chunk, server_cur.description,
                                               table, dest_index)
                push_start_time = time.time()
                log.info('Pushing ' + str(len(es_batch)) +
                         ' docs to Elasticsearch.')
                # Bulk upload to Elasticsearch in parallel.
                list(helpers.parallel_bulk(self.es, es_batch, chunk_size=400))
                upload_time = time.time() - push_start_time
                upload_rate = len(es_batch) / upload_time
                log.info(
                    'Elasticsearch up: batch_size={}, uploaded_per_second={}'
                    .format(len(es_batch), upload_rate)
                )
                num_converted_documents += len(chunk)
            log.info('Synchronized ' + str(num_converted_documents) + ' from '
                     'table \'' + table + '\' to Elasticsearch')
        pg_conn.commit()
        pg_conn.close()

    def _consistency_check(self, new_index, live_alias):
        """
        Indexing can fail for a number of reasons, such as a full disk inside of
        the Elasticsearch cluster, network errors that occurred during
        synchronization, and numerous other scenarios. This function does some
        basic comparison between the new search index and the database. If this
        check fails, an alert gets raised and the old index will be left in
        place. An operator must then investigate and either manually set the
        alias or remediate whatever circumstances interrupted the indexing job
        before running the indexing job once more.

        :param new_index: The newly created but not yet live index
        :param live_alias: The name of the live index
        :return: bool
        """
        if not self.es.indices.exists(index=live_alias):
            return True
        log.info('Refreshing and performing sanity check...')
        self.es.indices.refresh(index=new_index)
        _, last_doc_uuid = self._get_last_item_ids(live_alias)
        query = {
            "query": {
                "constant_score": {
                    "filter": {
                        "term": {
                            "identifier": str(last_doc_uuid)
                        }
                    }
                }
            }
        }
        last_doc_es = self.es.search(index=new_index, body=query)
        return True if last_doc_es['hits']['total'] else False

    def _go_live(self, write_index, live_alias):
        """
        Point the live index alias at the index we just created. Delete the
        previous one.
        """
        if not self._consistency_check(write_index, live_alias):
            msg = 'Reindexing failed; index {} does not appear to have all ' \
                  'of the documents in the database.'.format(write_index)
            log.error(msg)
        indices = set(self.es.indices.get('*'))
        # If the index exists already and it's not an alias, delete it.
        if live_alias in indices:
            log.warning('Live index already exists. Deleting and realiasing.')
            self.es.indices.delete(index=live_alias)
        # Create or update the alias so it points to the new index.
        if self.es.indices.exists_alias(live_alias):
            old = list(self.es.indices.get(live_alias).keys())[0]
            index_update = {
                'actions': [
                    {'remove': {'index': old, 'alias': live_alias}},
                    {'add': {'index': write_index, 'alias': live_alias}}
                ]
            }
            self.es.indices.update_aliases(index_update)
            log.info(
                'Updated \'{}\' index alias to point to {}'
                .format(live_alias, write_index)
            )
            log.info('Deleting old index {}'.format(old))
            self.es.indices.delete(index=old)
        else:
            self.es.indices.put_alias(index=write_index, name=live_alias)
            log.info(
                'Created \'{}\' index alias pointing to {}'
                .format(live_alias, write_index)
            )

    @staticmethod
    def _create_write_index(index_name: str):
        suffix = uuid.uuid4().hex
        write_name = index_name + '-' + suffix
        return write_name

    def listen(self, poll_interval=10):
        """
        Poll the database for changes every poll_interval seconds.

        :arg poll_interval: The number of seconds to wait before polling the
        database for changes.
        """
        while True:
            log.info('Listening for updates...')
            try:
                for table in self.tables_to_watch:
                    self._synchronize(table)
            except ElasticsearchConnectionError:
                self.es = elasticsearch_connect()
            time.sleep(poll_interval)

    def reindex(self, model_name: str):
        """
        Copy contents of the database to a new Elasticsearch index. Create an
        index alias to make the new index the "live" index when finished.
        """
        destination_index = self._create_write_index(model_name)
        self._synchronize(model_name, dest_idx=destination_index)
        self._go_live(destination_index, model_name)

    @staticmethod
    def pg_chunk_to_es(pg_chunk, columns, origin_table, dest_index):
        """
        Given a list of psycopg2 results, convert them all to Elasticsearch
        documents.
        """
        # Map column names to locations in the row tuple
        schema = {col[0]: idx for idx, col in enumerate(columns)}
        try:
            model = database_table_to_elasticsearch_model[origin_table]
        except KeyError:
            log.error(
                'Table ' + origin_table +
                ' is not defined in elasticsearch_models.')
            return []

        documents = []
        for row in pg_chunk:
            converted = model.database_row_to_elasticsearch_doc(row, schema)
            converted = converted.to_dict(include_meta=True)
            if dest_index:
                converted['_index'] = dest_index
            documents.append(converted)

        return documents


def elasticsearch_connect(timeout=300):
    """
    Repeatedly try to connect to Elasticsearch until successful.
    :return: An Elasticsearch connection object.
    """
    while True:
        try:
            return _elasticsearch_connect(timeout)
        except ElasticsearchConnectionError as e:
            log.exception(e)
            log.error('Reconnecting to Elasticsearch in 5 seconds. . .')
            time.sleep(5)
            continue


def _elasticsearch_connect(timeout=300):
    """
    Connect to configured Elasticsearch domain.

    :param timeout: How long to wait before ANY request to Elasticsearch times
    out. Because we use parallel bulk uploads (which sometimes wait long periods
    of time before beginning execution), a value of at least 30 seconds is
    recommended.
    :return: An Elasticsearch connection object.
    """

    log.info(
        'Connecting to %s %s with AWS auth', ELASTICSEARCH_URL,
        ELASTICSEARCH_PORT)
    auth = AWSRequestsAuth(
        aws_access_key=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_host=ELASTICSEARCH_URL,
        aws_region=AWS_REGION,
        aws_service='es'
    )
    auth.encode = lambda x: bytes(x.encode('utf-8'))
    es = Elasticsearch(
        host=ELASTICSEARCH_URL,
        port=ELASTICSEARCH_PORT,
        connection_class=RequestsHttpConnection,
        timeout=timeout,
        max_retries=10,
        retry_on_timeout=True,
        http_auth=auth,
        wait_for_status='yellow'
    )
    es.info()
    return es


def database_connect():
    """
    Repeatedly try to connect to database until successful.
    :return: A database connection object
    """
    while True:
        try:
            conn = psycopg2.connect(
                dbname=DATABASE_NAME,
                user=DATABASE_USER,
                password=DATABASE_PASSWORD,
                host=DATABASE_HOST,
                port=DATABASE_PORT,
                connect_timeout=5
            )
        except psycopg2.OperationalError as e:
            log.exception(e)
            log.error('Reconnecting to database in 5 seconds. . .')
            time.sleep(5)
            continue
        break

    return conn


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--reindex',
        default=None,
        help='Reindex data from a specific model in the database. Data is '
             'copied to a new index and then made \'live\' using index aliases,'
             ' making it possible to reindex without downtime.'
    )
    parsed = parser.parse_args()
    fmt = "%(asctime)s %(message)s"
    log.basicConfig(stream=sys.stdout, level=log.INFO, format=fmt)
    log.getLogger(ElasticsearchSyncer.__name__).setLevel(log.DEBUG)
    log.info('Connecting to database')
    # Use readonly and autocommit to prevent polling from locking tables.
    log.info('Connecting to Elasticsearch')
    elasticsearch = elasticsearch_connect()
    syncer = ElasticsearchSyncer(elasticsearch, replicate_tables)
    if parsed.reindex:
        log.info('Reindexing {}'.format(parsed.reindex))
        syncer.reindex(parsed.reindex)
    else:
        log.info('Beginning synchronizer')
        syncer.listen(SYNCER_POLL_INTERVAL)
