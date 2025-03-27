"""
# Create Proportional By Source Staging Index DAG

This DAG is used to create a new staging Elasticsearch index that is a subset
of a staging source index, such that the proportions of records by source in
the new index is equal to the proportions of records by source in the source
index.


Required Dagrun Configuration parameters:

* media_type:         The media type for which to create a new index.
* percentage_of_prod: A float indicating the proportion of items to take from each
                      source from the total amount existing in the staging
                      source index

Optional params:

* source_index: An existing staging Elasticsearch index to use as the basis for
                the new index. If not provided, the index aliased to
                `<media_type>-filtered` will be used.
* should_delete_old_index:    If True, the index previously pointed to by the target
                                alias (if one exists) will be deleted.

## When this DAG runs

This DAG is on a `None` schedule and is run manually.

## Race conditions

Because this DAG runs on the staging elasticsearch cluster, it does _not_ interfere
 with the production `data_refresh` or `create_filtered_index` DAGs. However, it will
 fail immediately if any of the DAGs tagged as part of the `staging-es-concurrency`
 group are running.
"""

from datetime import datetime, timedelta

from airflow.decorators import dag
from airflow.models.param import Param
from airflow.utils.trigger_rule import TriggerRule

from common import elasticsearch as es
from common import slack
from common.constants import (
    AUDIO,
    DAG_DEFAULT_ARGS,
    MEDIA_TYPES,
    REFRESH_POKE_INTERVAL,
    STAGING,
)
from common.sensors.constants import STAGING_ES_CONCURRENCY_TAG
from common.sensors.utils import prevent_concurrency_with_dags_with_tag
from elasticsearch_cluster.create_proportional_by_source_staging_index import (
    create_proportional_by_source_staging_index as create_index,
)


DAG_ID = "create_proportional_by_source_staging_index"


@dag(
    dag_id=DAG_ID,
    default_args=DAG_DEFAULT_ARGS,
    schedule=None,
    start_date=datetime(2024, 1, 31),
    tags=["elasticsearch", STAGING_ES_CONCURRENCY_TAG],
    max_active_runs=1,
    catchup=False,
    doc_md=__doc__,
    params={
        "media_type": Param(
            default=AUDIO,
            enum=MEDIA_TYPES,
            description="The media type for which to create the index.",
        ),
        "percentage_of_prod": Param(
            default=0.5,
            type="number",
            exclusiveMinimum=0,
            maximum=1,
            description=(
                "The proportion of items to take of each provider from"
                " the total amount existing in the source index."
            ),
        ),
        "source_index": Param(
            default=None,
            type=["string", "null"],
            description=(
                "Optionally, the existing staging Elasticsearch index"
                " to use as the basis for the new index. If not provided,"
                " the index aliased to `<media_type>-filtered` will be used."
            ),
        ),
        "should_delete_old_index": Param(
            default=False,
            type="boolean",
            description=(
                "Whether to delete the index previously pointed to by the"
                " `{media_type}-subset-by-source` alias."
            ),
        ),
    },
    render_template_as_native_obj=True,
)
def create_proportional_by_source_staging_index():
    # Fail early if any conflicting DAGs are running
    prevent_concurrency = prevent_concurrency_with_dags_with_tag(
        tag=STAGING_ES_CONCURRENCY_TAG,
    )

    es_host = es.get_es_host(environment=STAGING)

    source_index_name = create_index.get_source_index(
        source_index="{{ params.source_index }}",
        media_type="{{ params.media_type }}",
    )

    source_config = es.get_index_configuration(
        source_index=source_index_name, es_host=es_host
    )

    destination_index_name = create_index.get_destination_index_name(
        media_type="{{ params.media_type }}",
        current_datetime_str="{{ ts_nodash }}",
        percentage_of_prod="{{ params.percentage_of_prod }}",
    )

    destination_alias = create_index.get_destination_alias(
        media_type="{{ params.media_type }}"
    )

    destination_index_config = create_index.get_destination_index_config(
        source_config=source_config, destination_index_name=destination_index_name
    )

    new_index = es.create_index(index_config=destination_index_config, es_host=es_host)

    staging_source_counts = create_index.get_staging_source_counts(
        source_index=source_index_name, es_host=es_host
    )

    desired_source_counts = create_index.get_proportional_source_count_kwargs.override(
        task_id="get_desired_source_counts"
    )(
        staging_source_counts=staging_source_counts,
        percentage_of_prod="{{ params.percentage_of_prod }}",
    )

    reindex = es.trigger_and_wait_for_reindex.partial(
        destination_index=destination_index_name,
        source_index=source_index_name,
        timeout=timedelta(hours=12),
        requests_per_second="{{ var.value.get('ES_INDEX_THROTTLING_RATE', 20_000) }}",
        # When slices are used to parallelize indexing, max_docs does
        # not work reliably and the final proportions may be incorrect.
        slices=None,
        # Do not refresh the index after each partial reindex
        refresh=False,
        es_host=es_host,
        poke_interval=REFRESH_POKE_INTERVAL,
    ).expand_kwargs(desired_source_counts)

    refresh_destination_index = es.refresh_index(
        index_name=destination_index_name, es_host=es_host
    )

    point_alias = es.point_alias(
        es_host=es_host,
        target_index=destination_index_name,
        target_alias=destination_alias,
        should_delete_old_index="{{ params.should_delete_old_index }}",
    )

    notify_completion = slack.notify_slack.override(
        trigger_rule=TriggerRule.NONE_FAILED
    )(
        text=f"Reindexing complete for {destination_index_name}.",
        username="Proportional by Source Staging Index Creation",
        icon_emoji=":elasticsearch:",
    )

    # Setup additional dependencies
    prevent_concurrency >> es_host
    es_host >> [source_index_name, destination_index_name, destination_alias]
    staging_source_counts >> desired_source_counts
    new_index >> staging_source_counts
    reindex >> refresh_destination_index >> point_alias >> notify_completion


create_proportional_by_source_staging_index()
