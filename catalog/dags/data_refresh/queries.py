from textwrap import dedent


CREATE_FDW_EXTENSION_QUERY = "CREATE EXTENSION IF NOT EXISTS postgres_fdw"

CREATE_FDW_QUERY = dedent(
    """
    DROP SERVER IF EXISTS upstream CASCADE;
    CREATE SERVER upstream FOREIGN DATA WRAPPER postgres_fdw
        OPTIONS (host '{host}', dbname '{dbname}', port '{port}');

    CREATE USER MAPPING IF NOT EXISTS FOR deploy SERVER upstream
        OPTIONS (user '{user}', password '{password}');
    """
)

CREATE_SCHEMA_QUERY = dedent(
    """
    DROP SCHEMA IF EXISTS {schema_name} CASCADE;
    CREATE SCHEMA {schema_name} AUTHORIZATION deploy;

    IMPORT FOREIGN SCHEMA public LIMIT TO ({upstream_table_name})
        FROM SERVER upstream INTO {schema_name};
    """
)

CREATE_TEMP_TABLE_QUERY = dedent(
    """
    DROP TABLE IF EXISTS {temp_table_name};
    CREATE TABLE {temp_table_name} (LIKE {downstream_table_name} INCLUDING DEFAULTS
        INCLUDING CONSTRAINTS);
    """
)

ID_COLUMN_SETUP_QUERY = dedent(
    """
    ALTER TABLE {temp_table_name} ADD COLUMN IF NOT EXISTS
        id serial;
    CREATE SEQUENCE IF NOT EXISTS id_{temp_table_name}_seq;
    ALTER TABLE {temp_table_name} ALTER COLUMN
        id SET DEFAULT nextval('id_{temp_table_name}_seq'::regclass);
    """
)

TIMESTAMP_COLUMN_SETUP_QUERY = dedent(
    """
    ALTER TABLE {temp_table_name} ALTER COLUMN
        created_on SET DEFAULT CURRENT_TIMESTAMP;
    ALTER TABLE {temp_table_name} ALTER COLUMN
        updated_on SET DEFAULT CURRENT_TIMESTAMP;
    """
)

METRIC_COLUMN_SETUP_QUERY = dedent(
    """
    ALTER TABLE {temp_table_name} ADD COLUMN IF NOT EXISTS
        standardized_popularity double precision;
    ALTER TABLE {temp_table_name} ALTER COLUMN
        view_count SET DEFAULT 0;
    """
)

BASIC_COPY_DATA_QUERY = dedent(
    """
    INSERT INTO {temp_table_name} ({columns})
    SELECT {columns} FROM {schema_name}.{upstream_table_name}
    """
)

ADVANCED_COPY_DATA_QUERY = dedent(
    """
    INSERT INTO {temp_table_name} ({columns})
        SELECT {columns} from {schema_name}.{upstream_table_name} AS u
        WHERE NOT EXISTS(
            SELECT FROM {deleted_table_name} WHERE identifier = u.identifier
        )
    """
)

ADD_PRIMARY_KEY_QUERY = "ALTER TABLE {temp_table_name} ADD PRIMARY KEY (id);"

DROP_SERVER_QUERY = "DROP SERVER upstream CASCADE;"

SELECT_TABLE_INDICES_QUERY = (
    "SELECT indexdef FROM pg_indexes WHERE tablename='{table_name}';"
)

SELECT_ALL_CONSTRAINTS_QUERY = dedent(
    """
    SELECT conrelid::regclass AS table, conname, pg_get_constraintdef(c.oid)
    FROM pg_constraint AS c
    JOIN pg_namespace AS n
    ON n.oid = c.connamespace
    AND n.nspname = 'public'
    ORDER BY conrelid::regclass::text, contype DESC;
    """
)

ADD_CONSTRAINT_QUERY = "ALTER TABLE {constraint_table} ADD CONSTRAINT {constraint_name} {constraint_statement};"

DROP_CONSTRAINT_QUERY = (
    "ALTER TABLE {constraint_table} DROP CONSTRAINT {constraint_name};"
)

DELETE_ORPHANS_QUERY = dedent(
    """
    DELETE FROM {foreign_key_table} AS fk_table
    WHERE NOT EXISTS(
        SELECT 1 FROM {referenced_table} AS r
        WHERE r.{referenced_field} = fk_table.{foreign_key_field}
    );
    """
)

RENAME_INDEX_QUERY = "ALTER INDEX {old_name} RENAME TO {new_name};"

GO_LIVE_QUERY = dedent(
    """
    DROP TABLE {table_name};
    {restore_index_names}
    ALTER TABLE {temp_table_name} RENAME TO {table_name};
    """
)
