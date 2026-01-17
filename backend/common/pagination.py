from rest_framework.pagination import PageNumberPagination
from common.responses import success_response

class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination for SaaS resources.
    Allows clients to override page size using the `page_size` query parameter.
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return success_response(
            message='Data retrieved successfully',
            data={
                'count': self.page.paginator.count,
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
                'results': data
            },
        )
