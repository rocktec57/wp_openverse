from datetime import timedelta
from textwrap import dedent


DAG_ID = "add_rekognition_labels"
SLACK_USERNAME = "Rekognition Label Insertion"
SLACK_ICON = ":robot:"
REKOGNITION_PROVIDER = "rekognition"

# Task IDs used for branching operator
NOTIFY_START_TASK_ID = "notify_start"
NOTIFY_RESUME_TASK_ID = "notify_resume"

# File location in S3, can be overridden by a Variable at runtime
S3_BUCKET = "s3://migrated-cccatalog-archives"
S3_FILE_PREFIX = "kafka/image_analysis_labels-2020-12-17.txt"
# Current position in the file
CURRENT_POS_VAR_NAME = "REKOGNITION_LABEL_INSERTION_CURRENT_POSITION"
# In-memory buffer for records to insert into the temporary table
MEMORY_BUFFER_SIZE = 1_000
# In-memory buffer for reading from the file in S3
# See: https://github.com/piskvorky/smart_open/blob/a55794dee992dcebc3de23143c2c4a43ed3cc183/smart_open/s3.py#L70
FILE_BUFFER_SIZE = 5 * 1024 * 1024  # 5MB
# Limit to the number of failed records to keep track of
MAX_FAILED_RECORDS = 100

# Timeout for inserting a batch of records into the temporary table
INSERT_TIMEOUT = timedelta(minutes=2)
TEMP_TABLE_NAME = "rekognition_label_insertion"
# Copy the table definition using a query which will return no rows, but
# prevents us from having to be explicit about data types
CREATE_TEMP_TABLE_QUERY = f"""
    CREATE TABLE {TEMP_TABLE_NAME} AS
    SELECT identifier, tags
    FROM image
    WHERE 0=1;
    """
CREATE_TEMP_TABLE_INDEX_QUERY = f"CREATE UNIQUE INDEX ON {TEMP_TABLE_NAME}(identifier)"
SELECT_TEMP_TABLE_COUNT_QUERY = f"""
    SELECT COUNT(*)
    FROM {TEMP_TABLE_NAME};
    """
DROP_TABLE_QUERY = f"DROP TABLE IF EXISTS {TEMP_TABLE_NAME} CASCADE;"
BATCHED_UPDATE_CONFIG = {
    "query_id": f"{DAG_ID}_insertion",
    "table_name": "image",
    "select_query": dedent(f"""\
        WHERE identifier IN (SELECT identifier FROM {TEMP_TABLE_NAME})
    """),
    # Merge the tags from the temporary table with the existing tags.
    # Taken from _merge_jsonb_arrays in common.storage.columns
    "update_query": dedent(
        f"SET updated_on = NOW(), "
        f"""tags = COALESCE(
           (
             SELECT jsonb_agg(DISTINCT x)
             FROM jsonb_array_elements({TEMP_TABLE_NAME}.tags || image.tags) t(x)
           ),
           image.tags,
           {TEMP_TABLE_NAME}.tags
        )
        FROM {TEMP_TABLE_NAME}
        """
    ),
    "additional_where": f"AND {TEMP_TABLE_NAME}.identifier = image.identifier",
    "update_timeout": 60 * 60 * 5,
    "dry_run": False,
    "resume_update": False,
}

# Templated variables for the DAG
TEMPLATE_S3_PREFIX = (
    "{{ var.value.get('REKOGNITION_DATASET_PREFIX', '%s') }}" % S3_FILE_PREFIX  # noqa: UP031
)
TEMPLATE_IN_MEMORY_BUFFER_SIZE = (
    "{{ var.value.get('REKOGNITION_MEMORY_BUFFER_SIZE', %s) }}" % MEMORY_BUFFER_SIZE  # noqa: UP031
)
TEMPLATE_FILE_BUFFER_SIZE = (
    "{{ var.value.get('REKOGNITION_FILE_BUFFER_SIZE', %s) }}" % FILE_BUFFER_SIZE  # noqa: UP031
)

TEMPLATE_SLACK_MESSAGE_CONFIG = f"""
*Configuration*:
 - S3 prefix: `{S3_BUCKET}/{TEMPLATE_S3_PREFIX}`
 - In-memory buffer size: `{TEMPLATE_IN_MEMORY_BUFFER_SIZE}`
 - File buffer size: `{TEMPLATE_FILE_BUFFER_SIZE}`
"""
