# www.sparta-games.net

- Backend: https://github.com/creative-darkstar/sparta-games-BE
- Frontend: https://github.com/horang-e/sparta-games-FE

## 페이지 이용 안내
Unity를 사용하여 게임을 제작하고 WebGL로 빌드하여 이를 업로드 및 관리할 수 있는 사이트

- 누구나 게임을 플레이할 수 있습니다.
- 게임은 태그별, 조회수순, 평점순, 최신순으로 찾을 수 있습니다.
- 게임을 업로드할 땐, 로그인이 필요합니다.
- 게임태그를 추천하는 AI기능이 있습니다.
- 회원탈퇴는 문의를 남겨주세요.
  
<br>

## LandingPage


<br>

## GamePlayPage


<br>

## MyPage


<br>

### Reference

<div class="container" style="display: flex;">
<a href="https://itch.io/" style="margin-right: 10px;"><img src="https://img.shields.io/badge/itch.io-FA5C5C?style=for-the-badge&logo=itchdotio&logoColor=white"></a>

<a href="https://iogames.space/"><img src="https://img.shields.io/badge/iogames-ff6325?style=for-the-badge&logoColor=white"></a>
</div>

## 개요
 
### 주요 기능
- Unity로 제작한 게임의 WebGL 빌드 파일을 사이트에 업로드하고 이를 플레이할 수 있는 서비스를 제공

### 컨셉 및 목표
- 주니어 게임 개발자의 공간 제공 (커뮤니티)
- 유저로부터 피드백
- 한글화된 사이트를 서비스
- 협업에 도움이 될 수 있는 기능을 제공

## 개발 히스토리
- 2024-05-08 ~ 2024-06-12 : Sparta Games ver 1 developed
- 2024-06-12 : Sparta Games ver 1 launched
- 2024-06-13 ~ 2025-03-23 : Sparta Games ver 2 developed
- 2025-03-24 : Sparta Games ver 2 launched
- 2025-03-25 ~ : Sparta Games ver 2 - Community developing


## ERD

<br>

## Service Architecture

<br>

## API 명세

- Accounts

| Method                                 | Authorization | endpoint                     | Success | Fail       | Description   |
|----------------------------------------|---------------|------------------------------|---------|------------|---------------|
| <span style="color:yellow">POST</span> | `Anonymous`     | `/accounts/api/signup/` | 201,회원가입 성공       | 400,잘못된 사항 | 회원가입          |
| <span style="color:yellow">POST</span> | `Anonymous`     | `/accounts/api/login/` |    202,로그인 성공    |     401,Unauthorized       | 로그인           |
| <span style="color:yellow">POST</span> | `User`     | `/accounts/api/refresh/` |    200,OK     |    401,Unauthorized        | Refresh Token |
| <span style="color:yellow">POST</span>   | `User`     | `/accounts/api/logout/` |    200,로그아웃 완료    |     403, 로그아웃 실패       | 로그아웃          |

- Games

| Method                                 | Authorization | endpoint                      | Success                | Fail                           | Description      |
|----------------------------------------|---------------|-------------------------------|------------------------|--------------------------------|------------------|
| <span style="color:green">GET</span>   | `Anonymous`   | `/games/api/list/` | 200, 게임 리스트            | 404, 목록X                       | 게임 목록            |
| <span style="color:green">GET</span>   | `Anonymous`   | `/games/api/list/<int:game_pk>/` | 200, 게임 상세 정보          | 404, 목록X                       | 게임 상세페이지 / 댓글 조회 |
| <span style="color:yellow">POST</span> | `User`        | `/games/api/list/`              | 201, 게임 상세 정보          | 403 (회원이 아닙니다), 400 (필요한 정보)   | 게임 생성            |
| <span style="color:yellow">POST</span> | `Admin`       | `/games/api/list/<int:game_pk>/register/`          | 200, game_id, gamepath | 403 (권한이 없습니다)                 | 게임 등록            |
| <span style="color:yellow">POST</span> | `Admin`       | `/games/api/list/<int:game_pk>/deny/` | 200                    | 403 (권한이 없습니다)                 | 게임 등록 거부         |
| <span style="color:yellow">POST</span> | `Admin`       | `/games/api/list/<int:game_pk>/dzip/` | 200, 게임 zip 파일         | 403 (권한이 없습니다)                 | 게임 파일 다운         |
| <span style="color:skyblue">PUT</span> | `User`        | `/games/api/list/<int:game_pk>/` | 200, 게임 상세 정보          | 403 (작성자가 아닙니다)                | 게임 수정            |
| <span style="color:red">DELETE</span>  | `User`        | `/games/api/list/<int:game_pk>/` | 204, 삭제완료              | 403 (작성자가 아닙니다)                | 게임 삭제            |
| <span style="color:yellow">POST</span> | `User`        | `/games/api/list/<int:game_pk>/like/` | 200, like 정보           | 403 (회원이 아닙니다)                 | 게임 즐겨찾기          |
| <span style="color:yellow">POST</span> | `User`        | `/games/api/list/<int:game_pk>/star/` | 200, 별점 정보             | 403 (회원이 아닙니다)                 | 게임 별점 매기기        |
| <span style="color:yellow">POST</span> | `User`        | `/games/api/list/<int:game_pk>/comments/` | 200, 댓글 정보             | 403 (회원이 아닙니다), 400 (필요한것이있습니다) | 댓글 작성            |
| <span style="color:skyblue">PUT</span> | `User`        | `/games/api/comment/<int:comment:_id>/` | 201, 댓글 정보             | 403(작성자가 아닙니다)                 | 댓글 수정            |
| <span style="color:red">DELETE</span>  | `User`        | `/games/api/comment/<int:comment:_id>/` | 204, 삭제 완료             | 403(작성자가 아닙니다)                 | 댓글 삭제            |
| <span style="color:green">GET</span>   | `Admin`       | `/games/api/tags` | 200                    | 403(권한이 없습니다)                  | 태그 조회            |
| <span style="color:yellow">POST</span> | `Admin`        | `/games/api/tags` | 200                    | 403(권한이 없습니다)                  | 태그 생성            |
| <span style="color:red">DELETE</span>  | `Admin`        | `/games/api/tags` | 200                    | 403(권한이 없습니다)                  | 태그 삭제            |

- Users

| Method                                 | Authorization | endpoint                     | Success | Fail                          | Description       |
|----------------------------------------|---------------|------------------------------|---------|-------------------------------|-------------------|
| <span style="color:red">DELETE</span>  | `User`        | `/user/api/<int:user_pk>/` | 200,탈퇴 완료                   | 403 (회원이 아닙니다), 400 (비밀번호 틀림) | 회원 탈퇴             |
| <span style="color:skyblue">PUT</span> | `User`        | `/user/api/<int:user_pk>/password/` | 202,수정 완료          | 403 (회원이 아닙니다), 400 (비밀번호 틀림) | 패스워드 수정           |
| <span style="color:skyblue">PUT</span> | `User`        | `/user/api/<int:user_pk>/` | 202, 수정 완료          | 403 (회원이 아닙니다), 400 (비밀번호 틀림) | 프로필 수정 (이메일, 이미지) |
| <span style="color:green">GET</span>   | `Anonymous`   | `/user/api/<int:user_pk>/` | 200, 정보            | 404 목록X                       | 프로필 조회            |
| <span style="color:green">GET</span>   | `Anonymous`   | `/user/api/<int:user_pk>/games/` | 200, 정보            | 404 목록X                       | 내가 등록한 게임 목록      |
| <span style="color:green">GET</span>   | `User`   | `/user/api/<int:user_pk>/likes/` | 200, 정보            | 404 목록X                       | 내가 즐겨찾기한 게임 목록    |

- Qnas

| Method                                 | Authorization | endpoint                     | Success     | Fail                            | Description  |
|----------------------------------------|---------------|------------------------------|-------------|---------------------------------|--------------|
| <span style="color:green">GET</span>   | `Anonymous`   | `/qnas/api/post/` | 200, 리스트    | 404 (목록X)                       | QnA 목록 조회    |
| <span style="color:yellow">POST</span> | `Admin`        | `/qnas/api/post/` | 201, 문의내용   | 403 (회원이 아닙니다), 400 (필요한것이있습니다) | QnA 작성       |
| <span style="color:green">GET</span>   | `Anonymous`   | `/qnas/api/post/<int:post_pk>/` | 200, 리스트 상세 | 404 (목록 X)                      | QnA 상세페이지 조회 |
| <span style="color:skyblue">PUT</span> | `Admin`        | `/qnas/api/post/<int:post_pk>/` | 201, 문의 내용  | 403 (회원이 아닙니다), 400 (필요한 정보)    | QnA 수정       |
| <span style="color:red">DELETE</span>  | `Admin`        | `/qnas/api/post/<int:post_pk>/` | 204, 삭제 완료  | 404(목록X)  | QnA 삭제       |



## 역할 분담

- 정해진: 전체 일정 조정, 기능(Users, Accounts 위주) 구현, AWS 구조 구축

- ~~한진용(dropped out): 세부 일정 조정, 기능(Users, Accounts 위주) 구현, AWS 구조 구축~~

- 전관: 유효성 검증 등 기능 정밀화, 기능(Games, Qnas 위주) 구현

- 박성현: 프로젝트 관리 보조, 기능(Games, Qnas 위주) 구현, CD 구조 구축

- 임우재 튜터님(ver 1): S.A. 피드백, 프로젝트 방향성 피드백, 프로젝트 기술 질의 응답
    

## 사용하는 기술
<div id="python-badges" style="text-align: center;">
<img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white">
<img src="https://img.shields.io/badge/django-092E20?style=for-the-badge&logo=django&logoColor=white">
<img src="https://img.shields.io/badge/django rest framework-A30000?style=for-the-badge&logo=django&logoColor=white">
</div>
<div id="aws-badges" style="text-align: center;">
<img src="https://img.shields.io/badge/aws-232F3E?style=for-the-badge&logo=amazonwebservices&logoColor=white">
<img src="https://img.shields.io/badge/amazon ec2-FF9900?style=for-the-badge&logo=amazonec2&logoColor=white">
<img src="https://img.shields.io/badge/amazon rds-527FFF?style=for-the-badge&logo=amazonrds&logoColor=white">
<img src="https://img.shields.io/badge/amazon s3-569A31?style=for-the-badge&logo=amazons3&logoColor=white">
<img src="https://img.shields.io/badge/amazon route53-8C4FFF?style=for-the-badge&logo=amazonroute53&logoColor=white">
</div>
<div id="webserving-badges" style="text-align: center;">
<img src="https://img.shields.io/badge/nginx-009639?style=for-the-badge&logo=nginx&logoColor=white">
<img src="https://img.shields.io/badge/gunicorn-499848?style=for-the-badge&logo=gunicorn&logoColor=white">
</div>


## 설치 필요 패키지
- requirements.txt에 명시
- `pip install -r requirements.txt` 로 설치
