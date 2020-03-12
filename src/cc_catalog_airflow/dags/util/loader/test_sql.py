from collections import namedtuple
import json
import os
import time

import psycopg2
import pytest

from util.loader import sql

TEST_ID = 'testing'
POSTGRES_CONN_ID = os.getenv('TEST_CONN_ID')
POSTGRES_TEST_URI = os.getenv('AIRFLOW_CONN_POSTGRES_OPENLEDGER_TESTING')
TEST_LOAD_TABLE = f'provider_image_data{TEST_ID}'
TEST_IMAGE_TABLE = f'image_{TEST_ID}'


RESOURCES = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), 'test_resources'
)

DROP_LOAD_TABLE_QUERY = f'DROP TABLE IF EXISTS {TEST_LOAD_TABLE} CASCADE;'
DROP_IMAGE_TABLE_QUERY = f'DROP TABLE IF EXISTS {TEST_IMAGE_TABLE} CASCADE;'

CREATE_LOAD_TABLE_QUERY = (
        f'CREATE TABLE public.{TEST_LOAD_TABLE} ('
        f'foreign_identifier character varying(3000), '
        f'foreign_landing_url character varying(1000), '
        f'url character varying(3000), '
        f'thumbnail character varying(3000), '
        f'width integer, '
        f'height integer, '
        f'filesize character varying(100), '
        f'license character varying(50), '
        f'license_version character varying(25), '
        f'creator character varying(2000), '
        f'creator_url character varying(2000), '
        f'title character varying(5000), '
        f'meta_data jsonb, '
        f'tags jsonb, '
        f'watermarked boolean, '
        f'provider character varying(80), '
        f'source character varying(80)'
        f');'
)

UUID_FUNCTION_QUERY = (
    f'CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;'
)

CREATE_IMAGE_TABLE_QUERY = (
    f'CREATE TABLE public.{TEST_IMAGE_TABLE} ('
    f'id integer,'
    f'created_on timestamp with time zone NOT NULL,'
    f'updated_on timestamp with time zone NOT NULL,'
    f'identifier uuid DEFAULT public.uuid_generate_v4(),'
    f'perceptual_hash character varying(255),'
    f'provider character varying(80),'
    f'source character varying(80),'
    f'foreign_identifier character varying(3000),'
    f'foreign_landing_url character varying(1000),'
    f'url character varying(3000) NOT NULL,'
    f'thumbnail character varying(3000),'
    f'width integer,'
    f'height integer,'
    f'filesize integer,'
    f'license character varying(50) NOT NULL,'
    f'license_version character varying(25),'
    f'creator character varying(2000),'
    f'creator_url character varying(2000),'
    f'title character varying(5000),'
    f'tags_list character varying(255)[],'
    f'last_synced_with_source timestamp with time zone,'
    f'removed_from_source boolean NOT NULL,'
    f'meta_data jsonb,'
    f'tags jsonb,'
    f'watermarked boolean,'
    f'view_count integer DEFAULT 0 NOT NULL'
    f');'
)

UNIQUE_CONDITION_QUERY = (
    f"CREATE UNIQUE INDEX {TEST_IMAGE_TABLE}_provider_fid_url_key"
    f" ON public.{TEST_IMAGE_TABLE}"
    f" USING btree ("
    f"provider, md5((foreign_identifier)::text), md5((url)::text)"
    f");"
)

DROP_IMAGE_INDEX_QUERY = (
    f'DROP INDEX IF EXISTS {TEST_IMAGE_TABLE}_provider_fid_url_key;'
)


@pytest.fixture
def postgres():
    Postgres = namedtuple('Postgres', ['cursor', 'connection'])
    conn = psycopg2.connect(POSTGRES_TEST_URI)
    cur = conn.cursor()
    drop_command = f'DROP TABLE IF EXISTS {TEST_LOAD_TABLE}'
    cur.execute(drop_command)
    conn.commit()

    yield Postgres(cursor=cur, connection=conn)

    cur.execute(drop_command)
    cur.close()
    conn.commit()
    conn.close()


@pytest.fixture
def postgres_with_load_table():
    Postgres = namedtuple('Postgres', ['cursor', 'connection'])
    conn = psycopg2.connect(POSTGRES_TEST_URI)
    cur = conn.cursor()
    drop_command = f'DROP TABLE IF EXISTS {TEST_LOAD_TABLE}'
    cur.execute(drop_command)
    conn.commit()
    create_command = CREATE_LOAD_TABLE_QUERY
    cur.execute(create_command)
    conn.commit()

    yield Postgres(cursor=cur, connection=conn)

    cur.execute(drop_command)
    cur.close()
    conn.commit()
    conn.close()


@pytest.fixture
def postgres_with_load_and_image_table():
    Postgres = namedtuple('Postgres', ['cursor', 'connection'])
    conn = psycopg2.connect(POSTGRES_TEST_URI)
    cur = conn.cursor()

    cur.execute(DROP_LOAD_TABLE_QUERY)
    cur.execute(DROP_IMAGE_TABLE_QUERY)
    cur.execute(DROP_IMAGE_INDEX_QUERY)
    cur.execute(CREATE_LOAD_TABLE_QUERY)
    cur.execute(UUID_FUNCTION_QUERY)
    cur.execute(CREATE_IMAGE_TABLE_QUERY)
    cur.execute(UNIQUE_CONDITION_QUERY)

    conn.commit()

    yield Postgres(cursor=cur, connection=conn)

    cur.execute(DROP_LOAD_TABLE_QUERY)
    cur.execute(DROP_IMAGE_TABLE_QUERY)
    cur.execute(DROP_IMAGE_INDEX_QUERY)
    cur.close()
    conn.commit()
    conn.close()


def test_create_loading_table_creates_table(postgres):
    postgres_conn_id = POSTGRES_CONN_ID
    identifier = TEST_ID
    load_table = TEST_LOAD_TABLE
    sql.create_loading_table(postgres_conn_id, identifier)

    check_query = (
        f"SELECT EXISTS ("
        f"SELECT FROM pg_tables WHERE tablename='{load_table}');"
    )
    postgres.cursor.execute(check_query)
    check_result = postgres.cursor.fetchone()[0]
    assert check_result


def test_create_loading_table_errors_if_run_twice_with_same_id(postgres):
    postgres_conn_id = POSTGRES_CONN_ID
    identifier = TEST_ID
    sql.create_loading_table(postgres_conn_id, identifier)
    with pytest.raises(Exception):
        sql.create_loading_table(postgres_conn_id, identifier)


def test_import_data_loads_good_tsv(postgres_with_load_table, tmpdir):
    postgres_conn_id = POSTGRES_CONN_ID
    identifier = TEST_ID
    load_table = TEST_LOAD_TABLE
    tsv_file_name = os.path.join(RESOURCES, 'none_missing.tsv')
    with open(tsv_file_name) as f:
        f_data = f.read()

    test_tsv = 'test.tsv'
    path = tmpdir.join(test_tsv)
    path.write(f_data)

    sql.import_data_to_intermediate_table(
        postgres_conn_id,
        str(path),
        identifier
    )
    check_query = f'SELECT COUNT (*) FROM {load_table};'
    postgres_with_load_table.cursor.execute(check_query)
    num_rows = postgres_with_load_table.cursor.fetchone()[0]
    assert num_rows == 10


def test_import_data_deletes_null_url_rows(postgres_with_load_table, tmpdir):
    postgres_conn_id = POSTGRES_CONN_ID
    identifier = TEST_ID
    load_table = TEST_LOAD_TABLE
    tsv_file_name = os.path.join(RESOURCES, 'url_missing.tsv')
    with open(tsv_file_name) as f:
        f_data = f.read()

    test_tsv = 'test.tsv'
    path = tmpdir.join(test_tsv)
    path.write(f_data)

    sql.import_data_to_intermediate_table(
        postgres_conn_id,
        str(path),
        identifier
    )
    null_url_check = f'SELECT COUNT (*) FROM {load_table} WHERE url IS NULL;'
    postgres_with_load_table.cursor.execute(null_url_check)
    null_url_num_rows = postgres_with_load_table.cursor.fetchone()[0]
    remaining_row_count = f'SELECT COUNT (*) FROM {load_table};'
    postgres_with_load_table.cursor.execute(remaining_row_count)
    remaining_rows = postgres_with_load_table.cursor.fetchone()[0]

    assert null_url_num_rows == 0
    assert remaining_rows == 2


def test_import_data_deletes_null_license_rows(
        postgres_with_load_table, tmpdir
):
    postgres_conn_id = POSTGRES_CONN_ID
    identifier = TEST_ID
    load_table = TEST_LOAD_TABLE
    tsv_file_name = os.path.join(RESOURCES, 'license_missing.tsv')
    with open(tsv_file_name) as f:
        f_data = f.read()

    test_tsv = 'test.tsv'
    path = tmpdir.join(test_tsv)
    path.write(f_data)

    sql.import_data_to_intermediate_table(
        postgres_conn_id,
        str(path),
        identifier
    )
    license_check = (
        f'SELECT COUNT (*) FROM {load_table} WHERE license IS NULL;'
    )
    postgres_with_load_table.cursor.execute(license_check)
    null_license_num_rows = postgres_with_load_table.cursor.fetchone()[0]
    remaining_row_count = f'SELECT COUNT (*) FROM {load_table};'
    postgres_with_load_table.cursor.execute(remaining_row_count)
    remaining_rows = postgres_with_load_table.cursor.fetchone()[0]

    assert null_license_num_rows == 0
    assert remaining_rows == 2


def test_import_data_deletes_null_foreign_landing_url_rows(
        postgres_with_load_table, tmpdir
):
    postgres_conn_id = POSTGRES_CONN_ID
    identifier = TEST_ID
    load_table = TEST_LOAD_TABLE
    tsv_file_name = os.path.join(RESOURCES, 'foreign_landing_url_missing.tsv')
    with open(tsv_file_name) as f:
        f_data = f.read()

    test_tsv = 'test.tsv'
    path = tmpdir.join(test_tsv)
    path.write(f_data)

    sql.import_data_to_intermediate_table(
        postgres_conn_id,
        str(path),
        identifier
    )
    foreign_landing_url_check = (
        f'SELECT COUNT (*) FROM {load_table} '
        f'WHERE foreign_landing_url IS NULL;'
    )
    postgres_with_load_table.cursor.execute(foreign_landing_url_check)
    null_foreign_landing_url_num_rows = (
        postgres_with_load_table.cursor.fetchone()[0]
    )
    remaining_row_count = f'SELECT COUNT (*) FROM {load_table};'
    postgres_with_load_table.cursor.execute(remaining_row_count)
    remaining_rows = postgres_with_load_table.cursor.fetchone()[0]

    assert null_foreign_landing_url_num_rows == 0
    assert remaining_rows == 3


def test_import_data_deletes_null_foreign_identifier_rows(
        postgres_with_load_table, tmpdir
):
    postgres_conn_id = POSTGRES_CONN_ID
    identifier = TEST_ID
    load_table = TEST_LOAD_TABLE
    tsv_file_name = os.path.join(RESOURCES, 'foreign_identifier_missing.tsv')
    with open(tsv_file_name) as f:
        f_data = f.read()

    test_tsv = 'test.tsv'
    path = tmpdir.join(test_tsv)
    path.write(f_data)

    sql.import_data_to_intermediate_table(
        postgres_conn_id,
        str(path),
        identifier
    )
    foreign_identifier_check = (
        f'SELECT COUNT (*) FROM {load_table} '
        f'WHERE foreign_identifier IS NULL;'
    )
    postgres_with_load_table.cursor.execute(foreign_identifier_check)
    null_foreign_identifier_num_rows = (
        postgres_with_load_table.cursor.fetchone()[0]
    )
    remaining_row_count = f'SELECT COUNT (*) FROM {load_table};'
    postgres_with_load_table.cursor.execute(remaining_row_count)
    remaining_rows = postgres_with_load_table.cursor.fetchone()[0]

    assert null_foreign_identifier_num_rows == 0
    assert remaining_rows == 1


def test_import_data_deletes_duplicate_foreign_identifier_rows(
        postgres_with_load_table, tmpdir
):
    postgres_conn_id = POSTGRES_CONN_ID
    identifier = TEST_ID
    load_table = TEST_LOAD_TABLE
    tsv_file_name = os.path.join(RESOURCES, 'foreign_identifier_duplicate.tsv')
    with open(tsv_file_name) as f:
        f_data = f.read()

    test_tsv = 'test.tsv'
    path = tmpdir.join(test_tsv)
    path.write(f_data)

    sql.import_data_to_intermediate_table(
        postgres_conn_id,
        str(path),
        identifier
    )
    foreign_id_duplicate_check = (
        f"SELECT COUNT (*) FROM {load_table} "
        f"WHERE foreign_identifier='135257';"
    )
    postgres_with_load_table.cursor.execute(foreign_id_duplicate_check)
    foreign_id_duplicate_num_rows = (
        postgres_with_load_table.cursor.fetchone()[0]
    )
    remaining_row_count = f'SELECT COUNT (*) FROM {load_table};'
    postgres_with_load_table.cursor.execute(remaining_row_count)
    remaining_rows = postgres_with_load_table.cursor.fetchone()[0]

    assert foreign_id_duplicate_num_rows == 1
    assert remaining_rows == 3


def test_upsert_records_inserts_one_record_to_empty_image_table(
        postgres_with_load_and_image_table, tmpdir
):
    postgres_conn_id = POSTGRES_CONN_ID
    load_table = TEST_LOAD_TABLE
    image_table = TEST_IMAGE_TABLE
    identifier = TEST_ID

    FID = 'a'
    LAND_URL = 'https://images.com/a'
    IMG_URL = 'https://images.com/a/img.jpg'
    THM_URL = 'https://images.com/a/img_small.jpg'
    WIDTH = 1000
    HEIGHT = 500
    FILESIZE = 2000
    LICENSE = 'cc0'
    VERSION = '1.0'
    CREATOR = 'Alice'
    CREATOR_URL = 'https://alice.com'
    TITLE = 'My Great Pic'
    META_DATA = '{"description": "what a cool picture"}'
    TAGS = '["fun", "great"]'
    WATERMARKED = 'f'
    PROVIDER = 'images_provider'
    SOURCE = 'images_source'

    load_data_query = (
        f"INSERT INTO {load_table} VALUES("
        f"'{FID}','{LAND_URL}','{IMG_URL}','{THM_URL}','{WIDTH}','{HEIGHT}',"
        f"'{FILESIZE}','{LICENSE}','{VERSION}','{CREATOR}','{CREATOR_URL}',"
        f"'{TITLE}','{META_DATA}','{TAGS}','{WATERMARKED}','{PROVIDER}',"
        f"'{SOURCE}'"
        f");"
    )
    postgres_with_load_and_image_table.cursor.execute(load_data_query)
    postgres_with_load_and_image_table.connection.commit()
    sql.upsert_records_to_image_table(
        postgres_conn_id,
        identifier,
        image_table=image_table
    )
    postgres_with_load_and_image_table.cursor.execute(
        f"SELECT * FROM {image_table};"
    )
    actual_rows = postgres_with_load_and_image_table.cursor.fetchall()
    actual_row = actual_rows[0]
    assert len(actual_rows) == 1
    assert actual_row[5] == PROVIDER
    assert actual_row[6] == SOURCE
    assert actual_row[7] == FID
    assert actual_row[8] == LAND_URL
    assert actual_row[9] == IMG_URL
    assert actual_row[10] == THM_URL
    assert actual_row[11] == WIDTH
    assert actual_row[12] == HEIGHT
    assert actual_row[14] == LICENSE
    assert actual_row[15] == VERSION
    assert actual_row[16] == CREATOR
    assert actual_row[17] == CREATOR_URL
    assert actual_row[18] == TITLE
    assert actual_row[22] == json.loads(META_DATA)
    assert actual_row[23] == json.loads(TAGS)
    assert actual_row[24] is False


def test_upsert_records_inserts_two_records_to_image_table(
        postgres_with_load_and_image_table, tmpdir
):
    postgres_conn_id = POSTGRES_CONN_ID
    load_table = TEST_LOAD_TABLE
    image_table = TEST_IMAGE_TABLE
    identifier = TEST_ID

    FID_A = 'a'
    FID_B = 'b'
    LAND_URL_A = 'https://images.com/a'
    LAND_URL_B = 'https://images.com/b'
    IMG_URL_A = 'images.com/a/img.jpg'
    IMG_URL_B = 'images.com/b/img.jpg'
    LICENSE = 'cc0'
    VERSION = '1.0'
    PROVIDER = 'images'

    test_rows = [
        (FID_A, LAND_URL_A, IMG_URL_A, LICENSE, VERSION, PROVIDER),
        (FID_B, LAND_URL_B, IMG_URL_B, LICENSE, VERSION, PROVIDER)
    ]

    for r in test_rows:
        load_data_query = (
            f"INSERT INTO {load_table} ("
            f"foreign_identifier, foreign_landing_url, url,"
            f" license, license_version, provider, source"
            f") VALUES ("
            f"'{r[0]}', '{r[1]}', '{r[2]}',"
            f"'{r[3]}', '{r[4]}', '{r[5]}', '{r[5]}'"
            f");"
        )
        postgres_with_load_and_image_table.cursor.execute(load_data_query)
        postgres_with_load_and_image_table.connection.commit()
    sql.upsert_records_to_image_table(
        postgres_conn_id,
        identifier,
        image_table=image_table
    )
    postgres_with_load_and_image_table.cursor.execute(
        f"SELECT * FROM {image_table};"
    )
    actual_rows = postgres_with_load_and_image_table.cursor.fetchall()
    assert actual_rows[0][7] == FID_A
    assert actual_rows[1][7] == FID_B


def test_upsert_records_replaces_updated_on_and_last_synced_with_source(
        postgres_with_load_and_image_table, tmpdir
):
    postgres_conn_id = POSTGRES_CONN_ID
    load_table = TEST_LOAD_TABLE
    image_table = TEST_IMAGE_TABLE
    identifier = TEST_ID

    FID = 'a'
    LAND_URL = 'https://images.com/a'
    IMG_URL = 'images.com/a/img.jpg'
    LICENSE = 'cc0'
    VERSION = '1.0'
    PROVIDER = 'images'

    load_data_query = (
        f"INSERT INTO {load_table} ("
        f"foreign_identifier, foreign_landing_url, url,"
        f" license, license_version, provider, source"
        f") VALUES ("
        f"'{FID}','{LAND_URL}','{IMG_URL}',"
        f"'{LICENSE}','{VERSION}','{PROVIDER}', '{PROVIDER}'"
        f");"
    )
    postgres_with_load_and_image_table.cursor.execute(load_data_query)
    postgres_with_load_and_image_table.connection.commit()

    sql.upsert_records_to_image_table(
        postgres_conn_id,
        identifier,
        image_table=image_table
    )
    postgres_with_load_and_image_table.cursor.execute(
        f"SELECT * FROM {image_table};"
    )
    original_row = postgres_with_load_and_image_table.cursor.fetchall()[0]
    original_updated_on = original_row[2]
    original_last_synced = original_row[20]

    time.sleep(0.001)
    sql.upsert_records_to_image_table(
        postgres_conn_id,
        identifier,
        image_table=image_table
    )
    postgres_with_load_and_image_table.cursor.execute(
        f"SELECT * FROM {image_table};"
    )
    updated_result = postgres_with_load_and_image_table.cursor.fetchall()
    updated_row = updated_result[0]
    updated_updated_on = updated_row[2]
    updated_last_synced = updated_row[20]

    assert len(updated_result) == 1
    assert updated_updated_on > original_updated_on
    assert updated_last_synced > original_last_synced


def test_upsert_records_replaces_data(
        postgres_with_load_and_image_table, tmpdir
):
    postgres_conn_id = POSTGRES_CONN_ID
    load_table = TEST_LOAD_TABLE
    image_table = TEST_IMAGE_TABLE
    identifier = TEST_ID

    FID = 'a'
    PROVIDER = 'images_provider'
    SOURCE = 'images_source'
    WATERMARKED = 'f'
    IMG_URL = 'https://images.com/a/img.jpg'
    FILESIZE = 2000
    TAGS = '["fun", "great"]'

    LAND_URL_A = 'https://images.com/a'
    THM_URL_A = 'https://images.com/a/img_small.jpg'
    WIDTH_A = 1000
    HEIGHT_A = 500
    LICENSE_A = 'by'
    VERSION_A = '4.0'
    CREATOR_A = 'Alice'
    CREATOR_URL_A = 'https://alice.com'
    TITLE_A = 'My Great Pic'
    META_DATA_A = '{"description": "what a cool picture"}'

    LAND_URL_B = 'https://images.com/b'
    THM_URL_B = 'https://images.com/b/img_small.jpg'
    WIDTH_B = 2000
    HEIGHT_B = 1000
    LICENSE_B = 'cc0'
    VERSION_B = '1.0'
    CREATOR_B = 'Bob'
    CREATOR_URL_B = 'https://bob.com'
    TITLE_B = 'Bobs Great Pic'
    META_DATA_B = '{"description": "Bobs cool picture"}'

    load_data_query_a = (
        f"INSERT INTO {load_table} VALUES("
        f"'{FID}','{LAND_URL_A}','{IMG_URL}','{THM_URL_A}',"
        f"'{WIDTH_A}','{HEIGHT_A}','{FILESIZE}','{LICENSE_A}','{VERSION_A}',"
        f"'{CREATOR_A}','{CREATOR_URL_A}','{TITLE_A}','{META_DATA_A}',"
        f"'{TAGS}','{WATERMARKED}','{PROVIDER}','{SOURCE}'"
        f");"
    )
    postgres_with_load_and_image_table.cursor.execute(load_data_query_a)
    postgres_with_load_and_image_table.connection.commit()
    sql.upsert_records_to_image_table(
        postgres_conn_id,
        identifier,
        image_table=image_table
    )
    postgres_with_load_and_image_table.connection.commit()

    load_data_query_b = (
        f"INSERT INTO {load_table} VALUES("
        f"'{FID}','{LAND_URL_B}','{IMG_URL}','{THM_URL_B}',"
        f"'{WIDTH_B}','{HEIGHT_B}','{FILESIZE}','{LICENSE_B}','{VERSION_B}',"
        f"'{CREATOR_B}','{CREATOR_URL_B}','{TITLE_B}','{META_DATA_B}',"
        f"'{TAGS}','{WATERMARKED}','{PROVIDER}','{SOURCE}'"
        f");"
    )
    postgres_with_load_and_image_table.cursor.execute(
        f"DELETE FROM {load_table};"
    )
    postgres_with_load_and_image_table.connection.commit()
    postgres_with_load_and_image_table.cursor.execute(load_data_query_b)
    postgres_with_load_and_image_table.connection.commit()
    sql.upsert_records_to_image_table(
        postgres_conn_id,
        identifier,
        image_table=image_table
    )
    postgres_with_load_and_image_table.connection.commit()
    postgres_with_load_and_image_table.cursor.execute(
        f"SELECT * FROM {image_table};"
    )
    actual_rows = postgres_with_load_and_image_table.cursor.fetchall()
    actual_row = actual_rows[0]
    assert len(actual_rows) == 1
    assert actual_row[8] == LAND_URL_B
    assert actual_row[10] == THM_URL_B
    assert actual_row[11] == WIDTH_B
    assert actual_row[12] == HEIGHT_B
    assert actual_row[14] == LICENSE_B
    assert actual_row[15] == VERSION_B
    assert actual_row[16] == CREATOR_B
    assert actual_row[17] == CREATOR_URL_B
    assert actual_row[18] == TITLE_B
    assert actual_row[22] == json.loads(META_DATA_B)


def test_drop_load_table_drops_table(postgres_with_load_table):
    postgres_conn_id = POSTGRES_CONN_ID
    identifier = TEST_ID
    load_table = TEST_LOAD_TABLE
    sql.drop_load_table(postgres_conn_id, identifier)
    check_query = (
        f"SELECT EXISTS ("
        f"SELECT FROM pg_tables WHERE tablename='{load_table}');"
    )
    postgres_with_load_table.cursor.execute(check_query)
    check_result = postgres_with_load_table.cursor.fetchone()[0]
    assert not check_result
