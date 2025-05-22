from rest_framework import status
from rest_framework.response import Response

def std_response(
    data=None,
    message=None,
    status="error",
    pagination=None,
    error_code=None,
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
):
    response = {
        "status": status,
        "message": message,
        "data": data,
        "pagination": pagination,
        "error_code": error_code
    }
    return Response(response, status=status_code)
