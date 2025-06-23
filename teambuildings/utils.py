from bs4 import BeautifulSoup
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
                print(base_url)
                print("★★★★★★★★★★★★★★★★★")
                tmp = urljoin(base_url, src)
                print(tmp)
                results.append(tmp)
    
    return results


def delete_srcs(old_srcs, new_srcs):
    delete_list = []
    
    for item in old_srcs:
        if item not in new_srcs:
            delete_list.append(item)
    
    return delete_list
