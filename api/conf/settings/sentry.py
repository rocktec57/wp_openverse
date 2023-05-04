import sentry_sdk
from decouple import config
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import ignore_logger


SENTRY_DSN = config("SENTRY_DSN", default="")

SENTRY_SAMPLE_RATE = config("SENTRY_SAMPLE_RATE", default=1.0, cast=float)

ENVIRONMENT = config("ENVIRONMENT", default="local")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DJANGO_DEBUG_ENABLED", default=False, cast=bool)
if not DEBUG and SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=SENTRY_SAMPLE_RATE,
        send_default_pii=False,
        environment=ENVIRONMENT,
    )

    # ALLOW_HOSTS is correctly configured so ignore this to prevent
    # spammy bots like https://github.com/robertdavidgraham/masscan
    # from pushing un-actionable alerts to Sentry like
    # https://sentry.io/share/issue/9af3cdf8ef74420aa7bbb6697760a82c/
    ignore_logger("django.security.DisallowedHost")
