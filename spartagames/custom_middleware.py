from django.utils.deprecation import MiddlewareMixin

class CustomXFrameOptionsMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        # 로컬 환경의 React 앱 주소를 허용
        if request.get_host() in ['127.0.0.1:8000', 'localhost:5173', 'sparta-games.net','spartagames-git-dev-horanges-projects.vercel.app','spartagames-horanges-projects.vercel.app']:
            response['X-Frame-Options'] = 'ALLOWALL'  # 필요에 따라 'DENY'로 변경 가능
        else:
            response['X-Frame-Options'] = 'SAMEORIGIN'  # 기본 값 유지
        return response