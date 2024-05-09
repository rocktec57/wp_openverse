"""
# Update Science Museum URLs

One-time maintenance DAG to update Science Museum records to have valid URLs. See https://github.com/WordPress/openverse/issues/4261.

For each Science Museum record, this DAG:

* updates the url to the new format, excluding `/images/` in the path if it exists
* validates whether the url is reachable. If not, the record ID is added to an `invalid_science_musem_ids` table.

Once complete, we can use the `science_museum_invalid_ids` to identify records to delete. They are not automatically deleted by this DAG, in order to give us an opportunity to first see how many there are.
"""

import itertools
import logging
from datetime import timedelta
from textwrap import dedent

from airflow.decorators import dag, task
from airflow.exceptions import AirflowSkipException
from airflow.models.abstractoperator import AbstractOperator
from airflow.models.param import Param

from common import slack
from common.constants import DAG_DEFAULT_ARGS, POSTGRES_CONN_ID
from common.sql import RETURN_ROW_COUNT, PostgresHook
from common.urls import rewrite_redirected_url


logger = logging.getLogger(__name__)


DAG_ID = "update_science_museum_urls"
INVALID_IDS_TABLE = "science_museum_invalid_ids"
IDS_TO_UPDATE_TABLE = "temp_science_museum_rows_to_validate"

UPDATE_URLS_QUERY = dedent(
    """
    UPDATE image
    SET url=REPLACE(url, '/images', '')
    WHERE provider='sciencemuseum' AND url ILIKE '%/images/%';
    """
)
CREATE_TABLE_QUERY = dedent(
    f"""
    CREATE TABLE IF NOT EXISTS {INVALID_IDS_TABLE}
    (identifier uuid);
    """
)
CREATE_TEMP_TABLE_QUERY = dedent(
    f"""
    CREATE TABLE {IDS_TO_UPDATE_TABLE} AS
    SELECT ROW_NUMBER() OVER() row_id, identifier, url
    FROM image
    WHERE provider='sciencemuseum';
    """
)
DROP_TEMP_TABLE_QUERY = f"DROP TABLE {IDS_TO_UPDATE_TABLE};"
GET_BATCH_QUERY = dedent(
    """
    SELECT identifier, url
    FROM {table_name}
    WHERE row_id > {start} AND row_id <= {end};
    """
)


@task
def run_sql(
    sql: str,
    handler: callable = None,
    postgres_conn_id: str = POSTGRES_CONN_ID,
    task: AbstractOperator = None,
):
    postgres = PostgresHook(
        postgres_conn_id=postgres_conn_id,
        default_statement_timeout=PostgresHook.get_execution_timeout(task),
    )

    return postgres.run(sql, handler=handler)


@task
def get_batches(
    total_count: int,
    batch_size: int,
):
    return [
        {"start": i, "end": i + batch_size} for i in range(0, total_count, batch_size)
    ]


@task(max_active_tis_per_dagrun=3)
def process_batch(
    start: int,
    end: int,
    postgres_conn_id: str = POSTGRES_CONN_ID,
    task: AbstractOperator = None,
):
    invalid_ids = []

    postgres = PostgresHook(
        postgres_conn_id=postgres_conn_id,
        default_statement_timeout=PostgresHook.get_execution_timeout(task),
    )
    records = postgres.get_records(
        GET_BATCH_QUERY.format(table_name=IDS_TO_UPDATE_TABLE, start=start, end=end)
    )

    for identifier, url in records:
        # Failed to reach URL
        if rewrite_redirected_url(url) is None:
            invalid_ids.append(identifier)

    return invalid_ids


@task
def record_invalid_ids(invalid_ids):
    # Chain together
    ids_to_record = itertools.chain.from_iterable(invalid_ids)

    if not ids_to_record:
        raise AirflowSkipException("No invalid urls found!")

    values = ", ".join([f"('{id}')" for id in ids_to_record])
    query = dedent(
        f"""
        INSERT INTO {INVALID_IDS_TABLE} (identifier)
        VALUES {values}
        """
    )

    return run_sql.function(sql=query, handler=RETURN_ROW_COUNT)


@task
def notify_slack(invalid_count: int):
    slack.send_message(
        f"Detected {invalid_count} invalid Science Museum urls.", dag_id=DAG_ID
    )


@dag(
    dag_id=DAG_ID,
    schedule=None,
    catchup=False,
    tags=["data_normalization"],
    doc_md=__doc__,
    default_args={
        **DAG_DEFAULT_ARGS,
        "retries": 0,
        "execution_timeout": timedelta(days=2),
    },
    render_template_as_native_obj=True,
    params={
        "batch_size": Param(
            default=250,
            type="integer",
            description="The number of records to update per batch.",
        ),
    },
)
def update_science_museum_urls():
    # Update all URLs to have the correct format
    update = run_sql.override(task_id="update_url_format")(sql=UPDATE_URLS_QUERY)

    # Create table to track ids of records that still have an
    # invalid/unreachable url
    create_table = run_sql.override(task_id="create_invalid_id_table")(
        sql=CREATE_TABLE_QUERY
    )

    # Temp table used to store the information that needs to be
    # validated.
    create_temp_table = run_sql.override(task_id="create_temp_table")(
        sql=CREATE_TEMP_TABLE_QUERY, handler=RETURN_ROW_COUNT
    )

    # Split records into batches
    batches = get_batches(
        total_count=create_temp_table, batch_size="{{ params.batch_size }}"
    )

    # Verify each record's url
    process = process_batch.expand_kwargs(batches)

    # Record the identifiers of records with invalid urls
    record = record_invalid_ids(process)

    # Drop the temp table.
    drop_temp_table = run_sql.override(task_id="drop_temp_table")(
        sql=DROP_TEMP_TABLE_QUERY
    )

    # Report the number of invalid records to Slack
    notify_slack(record)

    update >> create_table >> process
    record >> drop_temp_table


update_science_museum_urls()
