from rest_framework.views import exception_handler
from .utils import std_response

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        return std_response(
            data=None,
            message=response.data.get("detail", "에러 발생"),
            status="error",
            error_code=response.status_code,
            status_code=response.status_code
        )

    return std_response(
        data=None,
        message=str(exc),
        status="error",
        error_code="SERVER_ERROR",
        status_code=500
    )


# def _handle_drf_exception(self, exception):
#         """
#         DRF 뷰에서 발생한 예외를 std_response로 처리
#         """
#         # 예외 타입별 처리
#         exception_handlers = {
#             'ValidationError': self._handle_validation_error,
#             'PermissionDenied': self._handle_permission_error,
#             'NotFound': self._handle_not_found_error,
#             'ParseError': self._handle_parse_error,
#             'AuthenticationFailed': self._handle_auth_error,
#         }
        
#         exception_name = exception.__class__.__name__
#         handler = exception_handlers.get(exception_name, self._handle_generic_error)
        
#         return handler(exception)
    
#     def _handle_validation_error(self, exception):
#         """유효성 검사 오류 처리"""
#         return std_response(
#             message="입력 데이터가 유효하지 않습니다",
#             status="error",
#             error_code="VALIDATION_ERROR",
#             status_code=status.HTTP_400_BAD_REQUEST
#         )
    
#     def _handle_permission_error(self, exception):
#         """권한 오류 처리"""
#         return std_response(
#             message="권한이 없습니다",
#             status="error", 
#             error_code="PERMISSION_DENIED",
#             status_code=status.HTTP_403_FORBIDDEN
#         )
    
#     def _handle_not_found_error(self, exception):
#         """404 오류 처리"""
#         return std_response(
#             message="요청한 리소스를 찾을 수 없습니다",
#             status="error",
#             error_code="NOT_FOUND",
#             status_code=status.HTTP_404_NOT_FOUND
#         )
    
#     def _handle_parse_error(self, exception):
#         """파싱 오류 처리"""
#         return std_response(
#             message="요청 데이터 형식이 올바르지 않습니다",
#             status="error",
#             error_code="PARSE_ERROR", 
#             status_code=status.HTTP_400_BAD_REQUEST
#         )
    
#     def _handle_auth_error(self, exception):
#         """인증 오류 처리"""
#         return std_response(
#             message="인증이 필요합니다",
#             status="error",
#             error_code="AUTHENTICATION_FAILED",
#             status_code=status.HTTP_401_UNAUTHORIZED
#         )
    
#     def _handle_generic_error(self, exception):
#         """일반적인 예외 처리"""
#         # 개발 환경에서는 상세 오류 정보 포함
#         import os
#         if os.getenv('DEBUG', 'False').lower() == 'true':
#             error_detail = str(exception)
#             print(f"미들웨어에서 처리된 예외: {exception.__class__.__name__}: {error_detail}")
#             print(f"Traceback: {traceback.format_exc()}")
#         else:
#             error_detail = "서버 내부 오류가 발생했습니다"
        
#         return std_response(
#             message=error_detail,
#             status="error",
#             error_code="INTERNAL_SERVER_ERROR",
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
#         )
