"""
CloudwatchWrapper extracted partially from
<https://github.com/awsdocs/aws-doc-sdk-examples/blob/54c3b82d8f9a12a862f9fcec44909829bda849af/python/example_code/cloudwatch/cloudwatch_basics.py>

The CloudwatchWrapper requires the AWS_CLOUDWATCH_CONN_ID, or the `aws_default`
connection, to be set in the Airflow Connections.

Modifying alarms can be skipped by setting the `TOGGLE_CLOUDWATCH_ALARMS` to `False`
in the Airflow Variables, which is particularly the desired behavior when running
the Data Refresh DAGs locally or in a development environment.
"""

import logging

from airflow.exceptions import AirflowSkipException
from airflow.models import Variable
from airflow.providers.amazon.aws.hooks.base_aws import AwsBaseHook
from botocore.exceptions import ClientError

from common.constants import AWS_CLOUDWATCH_CONN_ID


logger = logging.getLogger(__name__)


class CloudWatchWrapper:
    """Encapsulates Amazon CloudWatch functions"""

    def __init__(self, cloudwatch_resource):
        """:param cloudwatch_resource: A Boto3 CloudWatch resource."""
        self.cloudwatch_resource = cloudwatch_resource

    def enable_alarm_actions(self, alarm_name, enable):
        """
        Enable or disable actions on the specified alarm. Alarm actions can be
        used to send notifications or automate responses when an alarm enters a
        particular state.

        :param alarm_name: The name of the alarm.
        :param enable: When True, actions are enabled for the alarm. Otherwise, they
                       disabled.
        """
        try:
            alarm = self.cloudwatch_resource.Alarm(alarm_name)
            if enable:
                alarm.enable_actions()
            else:
                alarm.disable_actions()
            logger.info(
                "%s actions for alarm %s.",
                "Enabled" if enable else "Disabled",
                alarm_name,
            )
        except ClientError:
            logger.exception(
                "Couldn't %s actions alarm %s.",
                "enable" if enable else "disable",
                alarm_name,
            )
            raise


def enable_or_disable_alarms(enable):
    toggle = Variable.get("TOGGLE_CLOUDWATCH_ALARMS", True, deserialize_json=True)
    if not toggle:
        raise AirflowSkipException("TOGGLE_CLOUDWATCH_ALARMS is set to False.")

    cloudwatch = AwsBaseHook(
        aws_conn_id=AWS_CLOUDWATCH_CONN_ID,
        resource_type="cloudwatch",
    )
    cw_wrapper = CloudWatchWrapper(cloudwatch.get_conn())
    for percentage in [50, 90]:
        cw_wrapper.enable_alarm_actions(
            f"ES Production CPU utilization above {percentage}%", enable
        )
