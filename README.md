# www.sparta-games.net

- Backend: https://github.com/creative-darkstar/sparta-games-BE
- Frontend: https://github.com/horang-e/sparta-games-FE

## 페이지 이용 안내
Unity를 사용하여 게임을 제작하고 WebGL로 빌드하여 이를 업로드 및 관리할 수 있는 사이트

- 누구나 게임을 플레이할 수 있습니다.
- 게임은 카테고리 별로 분류하여 찾을 수 있고, 정렬은 조회수순, 평점순, 최신순으로 할 수 있습니다.
- 게임을 업로드할 땐, 로그인이 필요합니다.
- 회원탈퇴 후 회원 정보 삭제는 탈퇴일시로부터 24시간 뒤에 자동으로 완료됩니다.
  
<br>

## LandingPage


<br>
<p align="center">
  <img src="https://github.com/user-attachments/assets/4371f261-e4a6-4c95-bba1-66325dc031ce" height="540px" style="vertical-align: middle; margin-right: 20px;">
  <img src="https://github.com/user-attachments/assets/67dd59c2-02f9-4416-bc82-2022150324cf" height="540px" style="vertical-align: middle;">
</p>


## GamePlayPage


<br>
<p align="center">
  <img src="https://github.com/user-attachments/assets/35fc4d69-21c8-4b06-8a73-c16685067b6a" height="540px" style="vertical-align: middle;">
</p>

## MyPage


<br>
<p align="center">
  <img src="https://github.com/user-attachments/assets/86c85721-b189-4edd-8de9-f25517bcf816" height="540px" style="vertical-align: middle;">
</p>

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

![Image](https://github.com/user-attachments/assets/6fec5135-ea4f-4993-869d-40f57d6cd0ca)


## Service Architecture

<br>

## API Docs

<br>

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
