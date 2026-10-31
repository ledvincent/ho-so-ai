"""Recognise official procedure links and discover identity without a registry."""
import re
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from api.parse import ParseError, text

PORTAL_HOSTS = {'vpcp.dichvucong.gov.vn', 'dichvucong.gov.vn', 'thutuc.dichvucong.gov.vn'}
PORTAL_PATHS = {
    '/p/home/dvc-chi-tiet-thu-tuc-nganh-doc.html',
    '/p/home/dvc-chi-tiet-thu-tuc-dung-chung.html',
    '/p/home/dvc-chi-tiet-thu-tuc-hanh-chinh.html',
    '/p/home/dvc-tthc-thu-tuc-hanh-chinh-chi-tiet.html',
}
NATIONAL_CODE = r'\d\.\d{6}'


def is_portal_url(url):
    u = urlparse(url)
    ids = parse_qs(u.query).get('ma_thu_tuc', [])
    return (u.scheme == 'https' and u.hostname in PORTAL_HOSTS
            and u.port in (None, 443) and not u.username and not u.password
            and u.path in PORTAL_PATHS and len(ids) == 1
            and re.fullmatch(r'(?:\d+|\d\.\d{6}(?:\.[A-Za-z0-9]+)*)', ids[0]) is not None)


def portal_identity(raw, url):
    """Read page identity, never mistake a numeric page ID for a national code.

    Detail/legacy pages require resolution to the same national procedure's
    complete page. Local variants must not silently lose their local scope.
    No script from the page is executed.
    """
    if not is_portal_url(url):
        raise ParseError('Unsupported national portal procedure URL')
    soup = BeautifulSoup(raw.decode('utf-8-sig'), 'html.parser')
    scripts = '\n'.join(s.get_text() for s in soup.select('script'))
    inline = re.findall(r'\bobj\.procedure_code\s*=\s*[\'"]([^\'"]+)[\'"]', scripts)
    codes = inline + re.findall(r'\bvar\s+procedure_code\s*=\s*[\'"]([^\'"]+)[\'"]', scripts)
    for row in soup.select('.info-row'):
        label = row.select_one('.key')
        if label and text(label).rstrip(':').strip() == 'Mã thủ tục':
            values = row.find_all('div', recursive=False)
            if len(values) == 2:
                codes.append(text(values[1]))
    identities = set(codes)
    if len(identities) != 1:
        raise ParseError(f'Missing or conflicting procedure identity: {sorted(identities)!r}')
    code = identities.pop()
    if not re.fullmatch(NATIONAL_CODE, code):
        raise ParseError(f'Local procedure variant {code!r} needs a local-page adapter; '
                         'it cannot be replaced with the national procedure automatically')
    requested = parse_qs(urlparse(url).query)['ma_thu_tuc'][0]
    if '.' in requested and requested != code:
        raise ParseError(f'URL procedure code {requested!r} does not match page code {code!r}')
    names = [text(h) for h in soup.select('h1.main-title') if text(h)]
    if len(names) != 1:
        raise ParseError(f'Missing or ambiguous procedure name: {names!r}')
    resolved_url = None if inline else (
        'https://vpcp.dichvucong.gov.vn/p/home/dvc-chi-tiet-thu-tuc-nganh-doc.html?ma_thu_tuc=' + code)
    return code, names[0], resolved_url
