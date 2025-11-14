from PIL import Image
import os
import re
import requests
import stat
import zipfile

from django.db.models import Avg
from .models import Chip

from spartagames.config import DISCORD_GAME_UPLOAD_CHANNEL_WEBHOOK_URL
from spartagames.exceptions import DiscordAlertException


# zip bomb 체크용 최대 허용 압축률 (총 압축 해제된 파일들 용량 / 총 압축된 파일들 용량)
ZIP_RATIO_CUTOFF = 100.0

# Unity WebGL 빌드 게임폴더 내 Build 폴더명
UNITY_BUILD_DIR_NAME = "Build/"

# Unity WebGL 빌드 게임폴더 내 파일 확장자
UNITY_WASM_EXTENSIONS = (
    # 최신 버전
    ".wasm.unityweb", ".wasm.br", ".wasm.gz", ".wasm",
    # 2019 버전
    ".wasm.code.unityweb", ".wasm.code.br", ".wasm.code.gz",
    # 구버전
    ".asm.js", ".jsgz",
)
UNITY_FRAMEWORK_EXTENSIONS = (
    # 최신 버전
    ".framework.js.unityweb", ".framework.js.br", ".framework.js.gz", ".framework.js",
    # 2019 버전
    ".wasm.framework.unityweb", ".wasm.framework.br", ".wasm.framework.gz",
    # 구버전
    ".js.unityweb", ".js.br", ".js.gz",
)
UNITY_DATA_EXTENSIONS = (
    ".data.unityweb", ".data.br", ".data.gz", ".data",
)


def validate_image(image):
    """
    이미지 파일 형식만 검증하는 함수 (확장자 무관)
    """
    try:
        img = Image.open(image)
        img.verify()  # 파일 손상 여부 확인

        # 확실한 검증을 위해 다시 열어서 실제로 로드해보기
        img = Image.open(image)
        img.load()  # 로드 과정에서 오류 발생 시 비정상적인 이미지

        return True, None
    except Exception:
        return False, "유효한 이미지 파일이 아닙니다."


# 비정상적인 path 판단 (zip slip 사전 체크)
# 1) 절대경로('/' 또는 '\')
# 2) Windows 운영체제 기준 드라이브 루트 (C:/)
# 3) 경로를 이탈하려는 시도
def _is_abnormal_path(p: str) -> bool:
    path_for_check = p.replace('\\', '/')
    if path_for_check.startswith('./'):
        path_for_check = path_for_check[2:]
    
    if path_for_check.startswith(('/', '\\')) or re.match(r"^[a-zA-Z]:/", path_for_check):
        return True
    
    normpath_for_check = os.path.normpath(path_for_check).replace("\\", "/")
    if normpath_for_check.startswith("../") or ("/../" in normpath_for_check):
        return True

    return False


# symlink 확인
def _is_symlink(info: zipfile.ZipInfo) -> bool:
    # Unix 운영체제에서 만들어진 zip 파일일 때
    if info.create_system == 3:
        # external_attr 로부터 st_mode 를 추출한다
        # 상위 16 비트만 추출
        mode = (info.external_attr >> 16) & 0xFFFF
        # 해당 파일이 심볼릭 링크인지 bool 값 리턴
        return stat.S_ISLNK(mode)
    else:
        return False


def validate_zip_file(zip_file, max_size=500 * 1024 * 1024):
    """
    ZIP 파일의 크기 및 형식을 검증하는 함수
    """
    if not zip_file.name.endswith('.zip'):
        return False, "ZIP 파일만 업로드 가능합니다."

    if zip_file.size > max_size:
        return False, f"ZIP 파일 크기는 최대 {max_size / (1024 * 1024)}MB 이어야 합니다."

    # 2025-11-14 파일 CRC 검사(전수 검사) 하는 부분 주석 처리
    # 현재 게임 업로드 -> 게임 검수 완료 흐름 상 전수 검사 과정을 VirusTotal 에서 파일 검사하는 과정에 포함되어있으므로
    # 해당 과정을 임시 주석 처리
    # 나중에 외부 서비스를 사용하지 않고, 게임 업로더가 파일을 업로드하면서 내부적으로 검수를 하도록 만들 때
    # 해당 코드를 활용할 여지가 있음
    # 현재는 파일의 메타데이터 수준으로 검사하는 코드만 작성
    """
    try:
        with zipfile.ZipFile(zip_file, 'r') as zf:
            if zf.testzip() is not None:
                return False, "손상된 ZIP 파일입니다."
    except zipfile.BadZipFile:
        return False, "유효한 ZIP 파일이 아닙니다."
    """
    total_c = 0 # 총 압축된 파일들 용량
    total_u = 0 # 총 압축 해제된 파일들 용량
    try:
        with zipfile.ZipFile(zip_file, "r") as zf:
            infolist_of_files = [i for i in zf.infolist() if not i.is_dir()]
            names_of_files = []
            for i in infolist_of_files:
                if not i.filename.endswith('/'):
                    tmp_p = i.filename.replace('\\', '/')
                    names_of_files.append(tmp_p[2:] if tmp_p.startswith("./") else tmp_p)
            
            # 1. 비정상적인 path, 과도한 압축률(zip bomb), symlink 여부 확인, 암호화된 압축파일 여부 확인
            # a) 비정상적인 path 확인
            if any(_is_abnormal_path(n) for n in names_of_files):
                return False, "비정상적인 path가 존재합니다."
            
            # b) 과도한 압축률(zip bomb), symlink 여부 확인
            for info in infolist_of_files:
                # 압축률을 구하기 위해 total_c, total_u 계산
                total_c += getattr(info, "compress_size", 0)
                total_u += getattr(info, "file_size", 0)
                # b) 암호화된 압축파일 여부 확인
                # 16비트 플래그 필드의 LSB 기준 0번째 비트가 1이면 암호화된 파일
                if info.flag_bits & 0x1:
                    return False, "해당 zip 파일은 암호화된 상태입니다."
                # c) symlink 여부 확인
                if _is_symlink(info):
                    return False, "심볼릭 링크를 확인했습니다."
            
            # d) 압축률 확인
            if total_c > 0 and (total_u / total_c) > ZIP_RATIO_CUTOFF:
                return False, "zip bomb 이 의심되는 파일입니다."

            # 2. 파일 및 폴더 계층 구조 확인
            # a) index.html 이 루트 경로에 존재하는지 확인
            index_html_path = next((n for n in names_of_files if n.lower() == "index.html"), None)
            if not index_html_path:
                return False, "index.html 파일이 존재하지 않습니다."
            # b) 루트 경로 외 다른 index.html이 존재하는지 확인
            if any(n.lower().endswith("/index.html") for n in names_of_files):
                return False, "루트 폴더가 아닌 다른 경로에 index.html 파일이 존재합니다."

            # c) Build 폴더가 존재하는지 확인
            build_dir = UNITY_BUILD_DIR_NAME
            build_files = [n.lower() for n in names_of_files if n.startswith(build_dir)]
            if not build_files:
                return False, "Build 폴더가 존재하지 않습니다."

            # d) Build 폴더 내 파일들이 존재하는지 확인
            is_loader_exist = False
            is_wasm_exist = False
            is_framework_exist = False
            is_data_exist = False

            for f in build_files:
                if not is_loader_exist and (f.endswith(".loader.js") or f.endswith("unityloader.js")):
                    is_loader_exist = True
                if not is_wasm_exist and f.endswith(UNITY_WASM_EXTENSIONS):
                    is_wasm_exist = True
                if not is_framework_exist and f.endswith(UNITY_FRAMEWORK_EXTENSIONS):
                    is_framework_exist = True
                if not is_data_exist and f.endswith(UNITY_DATA_EXTENSIONS):
                    is_data_exist = True

            if not is_loader_exist: return False, "*.loader.js 또는 UnityLoader.js 형식의 파일이 존재하지 않습니다."
            if not is_wasm_exist: return False, "*.wasm[.gz|.br|.unityweb] 형식의 파일이 존재하지 않습니다."
            if not is_framework_exist: return False, "*.framework.js[.gz|.br|.unityweb] 형식의 파일이 존재하지 않습니다."
            if not is_data_exist: return False, "*.data[.gz|.br|.unityweb] 형식의 파일이 존재하지 않습니다."
    
    except Exception as e:
        return False, f"zip 파일을 검사하는 중 예외가 발생했습니다. ({e})"

    return True, None

def assign_chip_based_on_difficulty(game):
    """
    게임에 난이도 칩 부여 (EASY, NORMAL, HARD)
    난이도 평균을 이용함
    """
    #게임에 대한 평균 난이도
    average_difficulty = game.reviews.filter(is_visible=True).aggregate(
        average_difficulty=Avg('difficulty')
    )['average_difficulty'] or 0

    easy_chip, _ = Chip.objects.get_or_create(name="EASY")
    normal_chip, _ = Chip.objects.get_or_create(name="NORMAL")
    hard_chip, _ = Chip.objects.get_or_create(name="HARD")

    #기존 칩 제거
    game.chip.remove(easy_chip, normal_chip, hard_chip)

    #기준에 맞게 칩 부여
    if average_difficulty < 0.7:
        game.chip.add(easy_chip)
    elif average_difficulty > 1.3:
        game.chip.add(hard_chip)
    else:
        game.chip.add(normal_chip)


def send_discord_notification(game, msg_text="📢 새로운 게임이 업로드되었습니다! 관리자 계정으로 확인해주세요.\n"):
    webhook_url = DISCORD_GAME_UPLOAD_CHANNEL_WEBHOOK_URL

    message = {
        "content": f"""
{msg_text}
🎮 게임명: {game.title}\n"
👤 업로더: {game.maker.nickname}\n
"""
    }

    try:
        resp = requests.post(webhook_url, json=message)
        # resp.raise_for_status()
    except Exception as e:
        # logger 도입하는대로 해당 코드 라인은 살릴 예정
        # 지금은 print 처리
        # raise DiscordAlertException
        # 실패 시 로깅 처리
        print(f"Discord 알림 실패: {e}")
