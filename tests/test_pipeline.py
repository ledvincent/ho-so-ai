import json

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from api.config import ROOT, coverage
from api.fetch import allowed
from api.parse import ParseError, parse


def parsed(code):
    expected_name = {'1.004194':'Đăng ký tạm trú','1.002755':'Gia hạn tạm trú','1.004222':'Đăng ký thường trú','1.001146':'Gia hạn tạm trú cho người nước ngoài'}[code]
    manifest = json.loads((ROOT / "data/archive/raw/manifest.json").read_text())
    source = manifest[code]
    return parse((ROOT / source["raw_path"]).read_bytes(), code, source["url"], source["fetched_at"], expected_name)


@pytest.mark.parametrize("code", ["1.004194", "1.002755", "1.004222", "1.001146"])
def test_saved_pages(code):
    p = parsed(code)
    assert p["code"] == code
    assert p["source_url"].endswith(code)
    assert p["fetched_at"]
    assert p["requirements"] and p["methods"] and p["fees"]
    assert all(r["text_verbatim"] and r["originals"] >= 0 and r["copies"] >= 0 for r in p["requirements"])
    assert all(f["text_verbatim"] for f in p["fees"])
    assert all(allowed(f["url"]) for f in p["forms"])


def test_visible_fees_preserved_without_inventing_hidden_conditions():
    p = parsed("1.004194")
    assert {f["amount"] for f in p["fees"]} == {0, 5000, 7000, 10000, 15000}
    assert p["status"] == "parsed"
    assert len(p["fees"]) == 6
    assert len(p["requirements"]) == 9
    assert all(f["condition_status"] == "not_separately_stated" and f['condition_verbatim'] is None for f in p["fees"])
    assert all(f['detail_refs'] for f in p['fees'])
    assert not p['issues']
    assert len(p["forms"]) == 3


def test_full_sections_keep_method_descriptions_and_quantities():
    p = parsed('1.001146')
    full = ' '.join(' '.join(s['text_verbatim'].split()) for s in p['document']['sections'])
    assert len(p['document']['sections'])==6
    assert 'Đối tượng thực hiện' in full
    assert 'Xem chi tiết' not in full
    for method in p['methods']:
        assert method['description_verbatim'] in full
        assert method['processing_time_verbatim'] in full
    assert 'Bản chính:' in full and 'Bản sao:' in full
    assert all(r['text_verbatim'] in full for r in p['requirements'])


def test_foreigner_fee_currency():
    p = parsed("1.001146")
    assert p["status"] == "parsed"
    assert all(f["currency"] == "USD" and f["amount"] == 10 for f in p["fees"])


def test_shell_and_wrong_identity_rejected():
    with pytest.raises(ParseError):
        parse(b'<div id="root"></div>', "1.004194", "https://example.test", "2026-10-31", "Name")
    with pytest.raises(ParseError):
        parse((ROOT / "data/archive/raw/1.004194.html").read_bytes(), "1.004222", "https://example.test", "2026-10-31", "Đăng ký thường trú")


@pytest.mark.parametrize("url", ["http://127.0.0.1/", "https://evil.example/file", "https://csdl.dichvucong.gov.vn/web/jsp/download_file.jsp?ma=", "https://vpcp.dichvucong.gov.vn/p/home/dvc-chi-tiet-thu-tuc-nganh-doc.html?ma_thu_tuc=9.999999", "https://vpcp.dichvucong.gov.vn:444/p/home/dvc-chi-tiet-thu-tuc-nganh-doc.html?ma_thu_tuc=1.004194"])
def test_fetch_allowlist(url):
    assert not allowed(url)


def test_api_has_no_generated_answer_and_fails_closed(monkeypatch):
    from api.main import find, procedure, SearchRequest
    monkeypatch.delenv("SEARCH_MIN_SIMILARITY", raising=False)
    with pytest.raises(HTTPException) as error:
        find(SearchRequest(query="temporary residence"))
    assert error.value.status_code == 503
    with pytest.raises(ValidationError):
        SearchRequest(query="  ")
    monkeypatch.setattr("api.main.get_procedure", lambda code: None)
    with pytest.raises(HTTPException) as error:
        procedure("9.999999")
    assert error.value.status_code == 404


def test_embedding_dimensions_checked(monkeypatch):
    from api.search import embedding
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"data": [{"embedding": [1, 2]}]}
    monkeypatch.setattr("api.search.httpx.post", lambda *a, **k: Response())
    with pytest.raises(ValueError):
        embedding("synthetic input")
