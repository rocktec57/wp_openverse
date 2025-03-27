import re

from django.conf import settings

import schemathesis
from schemathesis.checks import content_type_conformance


schema = schemathesis.from_uri(f"{settings.CANONICAL_ORIGIN}/v1/schema/")


def status_code_aware_content_type_conformance(ctx, res, case):
    """
    Skip Content-Type conformance check when status code is 404.

    A status code of 404 can come from two sources:
    - Django sees the incoming URL and cannot map it to any endpoint.
      This returns an HTML response.
    - DRF gets the request but cannot map any object to the identifier.
      This returns a content-negotiated HTML/JSON response.

    Since the end user will likely not be using the data in the 404
    response anyway, we don't need the Content-Type to be validated.
    """

    if res.status_code == 404:
        return

    return content_type_conformance(ctx, res, case)


# The null-bytes Bearer tokens are skipped.
# The pattern identifies tests with headers that are acceptable,
# by only allowing authorization headers that use characters valid for
# token strings.
# In test, the token produces an inscruitable error,
# but condition is irreproducible in actual local or live
# environments. Once Schemathesis implements options
# to configure which headers are used
# (https://github.com/schemathesis/schemathesis/issues/2137)
# we will revisit these cases.
TOKEN_TEST_ACCEPTABLE = re.compile(r"^Bearer \w+$")


@schema.parametrize()
def test_schema(case: schemathesis.Case):
    if case.headers and not TOKEN_TEST_ACCEPTABLE.findall(
        case.headers.get("Authorization")
    ):
        # Do not use `pytest.skip` here, unfortunately it causes a deprecation warning
        # from schemathesis's implementation of `parameterize`.
        return

    case.call_and_validate(
        excluded_checks=[content_type_conformance],
        additional_checks=[status_code_aware_content_type_conformance],
    )
