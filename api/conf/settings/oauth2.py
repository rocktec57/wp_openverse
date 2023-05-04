from decouple import config

from conf.settings.base import INSTALLED_APPS, MIDDLEWARE


INSTALLED_APPS += [
    "oauth2_provider",
]

MIDDLEWARE += [
    "oauth2_provider.middleware.OAuth2TokenMiddleware",
]

OAUTH2_PROVIDER = {
    "SCOPES": {
        "read": "Read scope",
        "write": "Write scope",
    },
    "ACCESS_TOKEN_EXPIRE_SECONDS": config(
        "ACCESS_TOKEN_EXPIRE_SECONDS", default=3600 * 12, cast=int
    ),
}

OAUTH2_PROVIDER_APPLICATION_MODEL = "api.ThrottledApplication"
