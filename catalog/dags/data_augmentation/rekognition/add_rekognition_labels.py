import json
import logging

import smart_open
from airflow.decorators import task
from airflow.models import Variable
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.utils.trigger_rule import TriggerRule
from psycopg2.extras import Json

from common import slack
from common.constants import AWS_CONN_ID
from common.sql import PostgresHook
from data_augmentation.rekognition import constants, types
from data_augmentation.rekognition.label_mapping import LABEL_MAPPING


logger = logging.getLogger(__name__)


@task.branch
def resume_insertion():
    """
    Determine whether to skip table creation and indexing. This is based on the
    presence of the CURRENT_POS_VAR_NAME Variable when starting the DAG. If the
    Variable is present, assume that the DAG is resuming from an existing run,
    otherwise assume a fresh run.
    """
    if Variable.get(constants.CURRENT_POS_VAR_NAME, default_var=None):
        # Skip table creation and indexing
        return constants.NOTIFY_RESUME_TASK_ID
    return constants.NOTIFY_START_TASK_ID


def _process_labels(labels: list[types.Label]) -> list[types.MachineGeneratedTag]:
    tags = []
    for label in labels:
        name = label["Name"]
        # Map name if a correction exists for it
        name = LABEL_MAPPING.get(name, name)
        tags.append(
            {
                "name": name,
                # Confidence values need to be between 0 and 1
                "accuracy": label["Confidence"] / 100,
                "provider": constants.REKOGNITION_PROVIDER,
            }
        )
    return tags


def _insert_tags(tags_buffer: types.TagsBuffer, postgres_conn_id: str):
    logger.info(f"Inserting {len(tags_buffer)} records into the temporary table")
    postgres = PostgresHook(
        postgres_conn_id=postgres_conn_id,
        default_statement_timeout=constants.INSERT_TIMEOUT,
    )
    postgres.insert_rows(
        constants.TEMP_TABLE_NAME,
        tags_buffer,
        executemany=True,
        replace=True,
    )


@task(trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS)
def parse_and_insert_labels(
    s3_bucket: str,
    s3_prefix: str,
    in_memory_buffer_size: int,
    file_buffer_size: int,
    postgres_conn_id: str,
) -> types.ParseResults:
    tags_buffer: types.TagsBuffer = []
    failed_records = []
    total_processed = 0
    total_skipped = 0
    known_offset = Variable.get(
        constants.CURRENT_POS_VAR_NAME,
        default_var=None,
        deserialize_json=True,
    )

    # If an endpoint is defined for the hook, use the `get_client_type` method
    # to retrieve the S3 client. Otherwise, create the client from the session
    # so that Airflow doesn't override the endpoint default we want on the S3 client
    hook = S3Hook(aws_conn_id=AWS_CONN_ID)
    if hook.conn_config.endpoint_url:
        get_client = hook.get_client_type
    else:
        get_client = hook.get_session().client
    s3_client = get_client("s3")
    with smart_open.open(
        f"{s3_bucket}/{s3_prefix}",
        transport_params={"buffer_size": file_buffer_size, "client": s3_client},
    ) as file:
        # Navigate to known offset if available
        if known_offset:
            logger.info(f"Previous offset found, seeking to: {known_offset}")
            file.seek(known_offset)

        # Begin parsing the file
        # Cannot use "for blob in file" because we cannot iterate over the file
        # and also use file.tell() to get the current position
        while blob := file.readline():
            total_processed += 1
            try:
                labeled_image: types.LabeledImage = json.loads(blob)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON: {blob}")
                failed_records.append(blob)
                # If this many failures occur, something is likely systematically wrong
                if len(failed_records) >= constants.MAX_FAILED_RECORDS:
                    raise ValueError(
                        f"Over {constants.MAX_FAILED_RECORDS} failed records, "
                        f"systematic failure may be present. "
                        f"Check the logs to see what the issue may be."
                    )
                continue
            image_id = labeled_image["image_uuid"]
            raw_labels = labeled_image["response"]["Labels"]
            if not raw_labels:
                total_skipped += 1
                continue
            tags = _process_labels(raw_labels)
            tags_buffer.append((image_id, Json(tags)))

            if len(tags_buffer) >= in_memory_buffer_size:
                current_pos = file.tell()
                logger.info(f"Clearing buffer at position: {current_pos}")
                _insert_tags(tags_buffer, postgres_conn_id)
                Variable.set(
                    constants.CURRENT_POS_VAR_NAME,
                    value=file.tell(),
                    serialize_json=True,
                )
                tags_buffer.clear()

        # If there's anything left in the buffer, insert it
        if tags_buffer:
            _insert_tags(tags_buffer, postgres_conn_id)

        # Clear the offset if we've finished processing the file
        Variable.delete(constants.CURRENT_POS_VAR_NAME)

    return types.ParseResults(
        total_processed,
        total_skipped,
        len(failed_records),
        # Only share a sample of the failed records
        failed_records[:5],
    )


@task
def notify_parse_complete(results: types.ParseResults):
    message = f"""
Rekognition label parsing complete :rocket:
*Total processed:* {results.total_processed:,}
*Total skipped:* {results.total_skipped:,}
*Total failed:* {results.total_failed:,}
"""
    if results.failed_records_sample:
        message += "*Failed records sample*:\n"
        message += "\n".join([f" - `{rec}`" for rec in results.failed_records_sample])

    slack.send_message(
        message,
        constants.DAG_ID,
        constants.SLACK_USERNAME,
        icon_emoji=constants.SLACK_ICON,
    )
