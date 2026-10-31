from pathlib import Path
import pytest
from api.analysis import chunks, parse_ministry, validate_url
from api.parse import ParseError


def test_chunk_preserves_text_and_overlap():
    value = 'a'*1100+'b'*1100
    result = list(chunks(value))
    assert all(len(c)<=1200 for c in result)
    assert result[0][-150:]==result[1][:150]
    assert result[-1].endswith('b'*100)


@pytest.mark.parametrize('url',['https://evil.test/public_dir/form.doc','http://dichvucong.bocongan.gov.vn/public_dir/form.doc','https://vpcp.dichvucong.gov.vn/submit','https://127.0.0.1/public_dir/x.doc'])
def test_agent_rejects_untrusted_fetch_targets(url):
    with pytest.raises(ValueError):
        validate_url(url)


def test_agent_rejects_shell():
    with pytest.raises(ParseError):
        parse_ministry(b'<h4>Fake</h4>',dict(url='https://dichvucong.bocongan.gov.vn',sha256='0'*64,fetched_at='2026-10-31'))
