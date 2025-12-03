import uuid

from django.utils.deprecation import MiddlewareMixin
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.views import APIView

from .logging_context import set_request_context, clear_request_context


class CustomXFrameOptionsMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        # 로컬 환경의 React 앱 주소를 허용
        if request.get_host() in ['127.0.0.1:8000', 'localhost:5173', 'sparta-games.net','spartagames-git-dev-horanges-projects.vercel.app','spartagames-horanges-projects.vercel.app']:
            response['X-Frame-Options'] = 'ALLOWALL'  # 필요에 따라 'DENY'로 변경 가능
        else:
            response['X-Frame-Options'] = 'SAMEORIGIN'  # 기본 값 유지
        return response


class DRFStandardResponseMiddleware(MiddlewareMixin):
    """
    DRF 뷰에서 나오는 모든 응답을 std_response 형식으로 통일하는 미들웨어
    """
    
    def process_response(self, request, response):
        """
        DRF Response 객체만 처리
        """
        # DRF Response 객체인지 확인
        if isinstance(response, Response):
            # 이미 std_response 형식인지 확인
            if self._is_std_response_format(response.data):
                return response
            
            # std_response 형식으로 변환
            return self._wrap_drf_response(response)
        
        # DRF가 아닌 응답은 그대로 반환
        return response
    
    def _is_std_response_format(self, data):
        """
        이미 std_response 형식인지 확인
        """
        if isinstance(data, dict):
            # std_response의 필수 키들
            required_keys = {'status', 'message', 'data', 'pagination', 'error_code'}
            return required_keys.issubset(data.keys())
        return False
    
    def _wrap_drf_response(self, response):
        """
        DRF Response를 std_response 형식으로 래핑
        """
        original_data = response.data
        status_code = response.status_code
        
        # print(f"original_data는 {original_data}고 status_code는 {status_code} 임")
        
        # 성공/실패 상태 결정
        if 200 <= status_code < 300:
            response_status = "success"
            error_code = None
        else:
            response_status = "error"
            # 서버 단 에러 상황이 발생할 경우 다시 논의 필요. 현재는 THIRD_FAIL로 정의함 (2025-07-25)
            error_code = "THIRD_FAIL"
        
        # 상태 코드별 기본 메시지
        default_messages = {
            200: "요청이 성공적으로 처리되었습니다",
            201: "리소스가 성공적으로 생성되었습니다",
            204: "요청이 성공적으로 처리되었습니다",
            400: "잘못된 요청입니다",
            401: "인증이 필요합니다",
            403: "권한이 없습니다",
            404: "리소스를 찾을 수 없습니다",
            405: "허용되지 않은 메소드입니다",
            500: "서버 내부 오류가 발생했습니다"
        }
        
        message = default_messages.get(status_code, "처리 완료")
        
        # std_response 형식으로 데이터 구성
        std_data = {
            "status": response_status,
            "message": message,
            "data": original_data,
            "pagination": None,
            "error_code": error_code
        }
        
        # 기존 Response 객체의 데이터를 변경
        response.data = std_data
        response._is_rendered = False
        response.render()
        return response


class RequestContextMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        super().__init__(get_response)
        self.jwt_authenticator = JWTAuthentication()

    def __call__(self, request):
        try:
            request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
            request.request_id = request_id

            # JWT 기반 유저 확인
            user = getattr(request, "user", None)
            try:
                header = self.jwt_authenticator.get_header(request)
                if header is not None:
                    raw_token = self.jwt_authenticator.get_raw_token(header)
                    if raw_token is not None:
                        validated_token = self.jwt_authenticator.get_validated_token(raw_token)
                        user = self.jwt_authenticator.get_user(validated_token)
                        request.user = user  # Django 레벨에서 user 세팅
            except Exception:
                # 토큰이 없거나 잘못된 경우에는 그냥 anonymous 유지
                user = None
            
            if user and request.user.is_authenticated:
                user_id = request.user.pk
            else:
                user_id = "anonymous"

            set_request_context(
                request_id=request_id,
                user_id=user_id,
                path=request.path,
                method=request.method,
            )

            response = self.get_response(request)
            response["X-Request-ID"] = request_id
            return response
        finally:
            clear_request_context()
