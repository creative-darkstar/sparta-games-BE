from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin, urlparse

from .models import Role


def validate_want_roles(raw_roles):
    if isinstance(raw_roles, str):
        roles = [r.strip() for r in raw_roles.split(",") if r.strip()]
    elif isinstance(raw_roles, list):
        roles = [r.strip() for r in raw_roles if isinstance(r, str) and r.strip()]

    if len(roles) > 10:
        return None, "`want_roles`는 최대 10개까지 선택 가능합니다."

    valid_names = Role.objects.filter(name__in=roles).values_list("name", flat=True)
    invalid = [r for r in roles if r not in valid_names]
    if invalid:
        return None, f"유효하지 않은 역할 코드: {', '.join(invalid)}"

    return roles, None


def validate_choice(value, valid_choices, field_name):
    valid_keys = [choice[0] for choice in valid_choices]
    if value not in valid_keys:
        readable = ', '.join(valid_keys)
        return False, f"유효하지 않은 {field_name} 코드입니다.({readable} 중 하나)"
    return True, None


def is_absolute_url(url):
    parsed = urlparse(url)
    return parsed.scheme in ('http', 'https')


def extract_srcs(html_text, base_url):
    soup = BeautifulSoup(html_text, 'html.parser')
    imgs = soup.find_all('img')
    
    results = []

    for img in imgs:
        src = img.get('src')
        if src:
            if is_absolute_url(src):
                results.append(src)
            else:
                results.append(urljoin(base_url, src))
    
    return results


def parse_links(data):
    try:
        if hasattr(data, "getlist"):
            raw_list = data.getlist("portfolio")
        else:
            raw = data.get("portfolio", "[]")
            raw_list = json.loads(raw) if isinstance(raw, str) else raw

        parsed = []
        for i, item in enumerate(raw_list):
            if isinstance(item, str):
                item = json.loads(item)
            if isinstance(item, dict) and "link" in item:
                parsed.append(item)
            else:
                raise ValueError(f"portfolio[{i}] 항목이 JSON 객체가 아닙니다.")
        return parsed, None
    except Exception as e:
        return None, str(e)

def get_valid_duration_keys(base_duration: str):
        DURATION_ORDER = {
            "3M": 1,
            "6M": 2,
            "1Y": 3,
            "GT1Y": 4,
        }
        return [
            key for key, order in DURATION_ORDER.items()
            if order <= DURATION_ORDER.get(base_duration, 4)
        ]
