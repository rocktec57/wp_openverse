"""
# Add license URL

Add `license_url` to rows without one in their `meta_data` fields.
This PR merges the `meta_data` value with "{license_url: https://... }", where the
url is constructed from the `license` and `license_version` columns.

This is a maintenance DAG that should be run once.
"""

import logging
from datetime import timedelta
from textwrap import dedent

from airflow.decorators import dag, task
from airflow.exceptions import AirflowSkipException
from airflow.models.abstractoperator import AbstractOperator
from airflow.models.param import Param
from airflow.utils.state import State
from airflow.utils.trigger_rule import TriggerRule
from psycopg2._json import Json

from common import slack
from common.constants import DAG_DEFAULT_ARGS, POSTGRES_CONN_ID
from common.licenses import get_license_info_from_license_pair
from common.sql import RETURN_ROW_COUNT, PostgresHook


DAG_ID = "add_license_url"

logger = logging.getLogger(__name__)


def run_sql(
    sql: str,
    log_sql: bool = True,
    method: str = "get_records",
    handler: callable = None,
    autocommit: bool = False,
    postgres_conn_id: str = POSTGRES_CONN_ID,
    dag_task: AbstractOperator = None,
):
    postgres = PostgresHook(
        postgres_conn_id=postgres_conn_id,
        default_statement_timeout=PostgresHook.get_execution_timeout(dag_task),
        log_sql=log_sql,
    )
    if method == "get_records":
        return postgres.get_records(sql)
    elif method == "get_first":
        return postgres.get_first(sql)
    else:
        return postgres.run(sql, autocommit=autocommit, handler=handler)


@task
def get_license_groups(query: str, ti=None) -> list[tuple[str, str]]:
    """
    Get license groups of rows that don't have a `license_url` in their
    `meta_data` field.

    :return: List of (license, version) tuples.
    """
    license_groups = run_sql(query, dag_task=ti.task)

    total_nulls = sum(group[2] for group in license_groups)
    licenses_detailed = "\n".join(
        f"{group[0]} \t{group[1]} \t{group[2]}" for group in license_groups
    )

    message = f"""
Starting `{DAG_ID}` DAG. Found {len(license_groups)} license groups with {total_nulls}
records without `license_url` in `meta_data` left.\nCount per license-version:
{licenses_detailed}
    """
    slack.send_message(
        message,
        username="Airflow DAG Data Normalization - license_url",
        dag_id=DAG_ID,
    )

    return [(group[0], group[1]) for group in license_groups]


@task(max_active_tis_per_dag=1, execution_timeout=timedelta(hours=36))
def update_license_url(license_group: tuple[str, str], batch_size: int, ti=None) -> int:
    """
    Add license_url to meta_data batching all records with the same license.

    :param license_group: tuple of license and version
    :param batch_size: number of records to update in one update statement
    :param ti: automatically passed by Airflow, used to set the execution timeout.
    """
    license_, version = license_group
    license_info = get_license_info_from_license_pair(license_, version)
    if license_info is None:
        raise AirflowSkipException(
            f"No license pair ({license_}, {version}) in the license map."
        )
    *_, license_url = license_info

    logging.info(
        f"Will add `license_url` in `meta_data` for records with license "
        f"{license_} {version} to {license_url}."
    )
    license_url_dict = {"license_url": license_url}

    # Merge existing metadata with the new license_url
    update_query = dedent(
        f"""
        UPDATE image
        SET meta_data = ({Json(license_url_dict)}::jsonb || meta_data), updated_on = now()
        WHERE identifier IN (
            SELECT identifier
            FROM image
            WHERE license = '{license_}' AND license_version = '{version}'
                AND meta_data->>'license_url' IS NULL
            LIMIT {batch_size}
            FOR UPDATE SKIP LOCKED
        );
        """
    )
    total_updated = 0
    updated_count = 1
    while updated_count:
        updated_count = run_sql(
            update_query,
            log_sql=total_updated == 0,
            method="run",
            handler=RETURN_ROW_COUNT,
            autocommit=True,
            dag_task=ti.task,
        )
        total_updated += updated_count
    logger.info(f"Updated {total_updated} rows with {license_url}.")

    return total_updated


@task(trigger_rule=TriggerRule.ALL_DONE)
def report_completion(updated, query: str, ti=None):
    """
    Check for null in `meta_data` and send a message to Slack with the statistics
    of the DAG run.

    :param updated: total number of records updated
    :param query: SQL query to get the count of records left with `license_url` as NULL
    :param ti: automatically passed by Airflow, used to set the execution timeout.
    """
    total_updated = sum(updated) if updated else 0

    license_groups = run_sql(query, dag_task=ti.task)
    total_nulls = sum(group[2] for group in license_groups)
    licenses_detailed = "\n".join(
        f"{group[0]} \t{group[1]} \t{group[2]}" for group in license_groups
    )

    message = f"""
    `{DAG_ID}` DAG run completed. Updated {total_updated} record(s) with `license_url` in the
    `meta_data` field. Found {len(license_groups)} license groups with {total_nulls} record(s) left pending.
    """
    if total_nulls != 0:
        message += f"\nCount per license-version:\n{licenses_detailed}"

    slack.send_message(
        message,
        username="Airflow DAG Data Normalization - license_url",
        dag_id=DAG_ID,
    )


@task(trigger_rule=TriggerRule.ALL_DONE)
def report_failed_license_pairs(dag_run=None):
    """
    Send a message to Slack with the license-version pairs that could not be found
    in the license map.
    """
    skipped_tasks = [
        dag_task
        for dag_task in dag_run.get_task_instances(state=State.SKIPPED)
        if "update_license_url" in dag_task.task_id
    ]

    if not skipped_tasks:
        raise AirflowSkipException

    message = (
        f"""
    One or more license pairs could not be found in the license map while running
    the `{DAG_ID}` DAG. See the logs for more details:
    """
    ) + "\n".join(
        f"  - <{dag_task.log_url}|{dag_task.task_id}>" for dag_task in skipped_tasks[:5]
    )

    slack.send_alert(
        message,
        username="Airflow DAG Data Normalization - license_url",
        dag_id=DAG_ID,
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
        "execution_timeout": timedelta(hours=5),
    },
    render_template_as_native_obj=True,
    params={
        "batch_size": Param(
            default=10_000,
            type="integer",
            description="The number of records to update per batch.",
        ),
    },
)
def add_license_url():
    query = dedent("""
        SELECT license, license_version, count(identifier)
        FROM image WHERE meta_data->>'license_url' IS NULL
        GROUP BY license, license_version
    """)

    license_groups = get_license_groups(query)
    updated = update_license_url.partial(batch_size="{{ params.batch_size }}").expand(
        license_group=license_groups
    )
    report_completion(updated, query)
    updated >> report_failed_license_pairs()


add_license_url()
