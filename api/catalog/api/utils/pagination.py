from django.conf import settings
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    page_size_query_param = "page_size"
    page_query_param = "page"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.result_count = None  # populated later
        self.page_count = None  # populated later
        self.page = 1  # default, get's updated when necessary

    def get_paginated_response(self, data):
        return Response(
            {
                "result_count": self.result_count,
                "page_count": min(settings.MAX_PAGINATION_DEPTH, self.page_count),
                "page_size": self.page_size,
                "page": self.page,
                "results": data,
            }
        )

    def get_paginated_response_schema(self, schema):
        """
        Get the schema of the paginated response, used by `drf-spectacular` to
        generate the documentation of the paginated search results response.
        """

        field_descriptions = {
            "result_count": "The total number of items returned by search result.",
            "page_count": "The total number of pages returned by search result.",
            "page_size": "The number of items per page.",
            "page": "The current page number returned in the response.",
        }
        return {
            "type": "object",
            "properties": {
                field: {"type": "integer", "description": description}
                for field, description in field_descriptions.items()
            }
            | {"results": schema},
        }
