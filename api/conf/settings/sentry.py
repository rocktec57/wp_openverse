import sentry_sdk
from decouple import config
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration, ignore_logger

from conf.settings.base import ENVIRONMENT
from conf.settings.security import DEBUG


SENTRY_DSN = config("SENTRY_DSN", default="")

SENTRY_TRACES_SAMPLE_RATE = config("SENTRY_TRACES_SAMPLE_RATE", default=0, cast=float)
SENTRY_PROFILES_SAMPLE_RATE = config(
    "SENTRY_PROFILES_SAMPLE_RATE", default=0, cast=float
)

INTEGRATIONS = [
    DjangoIntegration(),
    # This prevents two errors from being sent to Sentry (one with the correct
    # information and the other with the logged JSON as the error name), since we
    # use JSON-logging as well which can conflict with the way Sentry expects alerts.
    # https://github.com/kiwicom/structlog-sentry?tab=readme-ov-file#logging-as-json
    LoggingIntegration(event_level=None, level=None),
]

if not DEBUG and SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=INTEGRATIONS,
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        profiles_sample_rate=SENTRY_PROFILES_SAMPLE_RATE,
        send_default_pii=False,
        environment=ENVIRONMENT,
    )

    # ALLOW_HOSTS is correctly configured so ignore this to prevent
    # spammy bots like https://github.com/robertdavidgraham/masscan
    # from pushing un-actionable alerts to Sentry like
    # https://sentry.io/share/issue/9af3cdf8ef74420aa7bbb6697760a82c/
    ignore_logger("django.security.DisallowedHost")
    # ``django-structlog`` writes ERROR logs when a response has a 5xx response
    # code, which can be registered by Sentry and obscure the underlying reason
    # why 5xx response was returned in the first place.
    ignore_logger("django_structlog.middlewares.request")
    # These errors can occur in large volumes and so we don't want them to fill
    # up in Sentry and overwhelm us with Slack notifications.
    ignore_logger("api.utils.check_dead_links._head")
