import hashlib
import json
from contextlib import contextmanager

import pytest
from bs4 import BeautifulSoup

from api import analysis
from api.config import ROOT
from api.parse import ParseError
from api.procedure_sources import is_portal_url, portal_identity


CANONICAL = 'https://vpcp.dichvucong.gov.vn/p/home/dvc-chi-tiet-thu-tuc-nganh-doc.html?ma_thu_tuc=1.004194'
DETAIL = 'https://dichvucong.gov.vn/p/home/dvc-tthc-thu-tuc-hanh-chinh-chi-tiet.html?ma_thu_tuc=5974'
RAW = (ROOT/'data/archive/raw/1.004194.html').read_bytes()


def detail_page(code='1.004194'):
    return f'''<h1 class="main-title">Đăng ký tạm trú</h1>
        <div class="info-row"><div class="key">Mã thủ tục:</div><div>{code}</div></div>'''.encode()


@pytest.mark.parametrize('host', ['vpcp.dichvucong.gov.vn', 'dichvucong.gov.vn', 'thutuc.dichvucong.gov.vn'])
@pytest.mark.parametrize('path', ['nganh-doc', 'dung-chung', 'hanh-chinh'])
def test_accepts_national_portal_aliases(host, path):
    url = f'https://{host}/p/home/dvc-chi-tiet-thu-tuc-{path}.html?ma_thu_tuc=1.004194'
    analysis.validate_url(url)
    code, name, resolved = portal_identity(RAW, url)
    assert (code, name, resolved) == ('1.004194', 'Đăng ký tạm trú', None)


@pytest.mark.parametrize('url', [
    DETAIL.replace('https:', 'http:'),
    DETAIL.replace('dichvucong.gov.vn', 'dichvucong.gov.vn.evil.test'),
    DETAIL.replace('dichvucong.gov.vn', 'user@dichvucong.gov.vn'),
    DETAIL.replace('dichvucong.gov.vn', 'dichvucong.gov.vn:444'),
    DETAIL + '&ma_thu_tuc=6007',
    DETAIL.replace('5974', '../etc/passwd'),
    DETAIL.replace('dvc-tthc-thu-tuc-hanh-chinh-chi-tiet.html', 'submit'),
])
def test_rejects_untrusted_or_ambiguous_procedure_links(url):
    assert not is_portal_url(url)
    with pytest.raises(ValueError):
        analysis.validate_url(url)


def test_numeric_id_is_resolved_from_page_not_treated_as_code():
    assert portal_identity(detail_page(), DETAIL) == ('1.004194', 'Đăng ký tạm trú', CANONICAL)


def test_legacy_script_identity_is_data_not_executed():
    raw = '<h1 class="main-title">Đăng ký tạm trú</h1><script>var procedure_code = "1.004194";</script>'.encode()
    assert portal_identity(raw, CANONICAL.replace('nganh-doc', 'hanh-chinh'))[2] == CANONICAL


def test_conflicting_identity_wrong_code_and_local_scope_fail_closed():
    with pytest.raises(ParseError, match='conflicting'):
        portal_identity(detail_page() + b'<script>obj.procedure_code = "1.004222";</script>', DETAIL)
    with pytest.raises(ParseError, match='does not match'):
        portal_identity(RAW, CANONICAL.replace('1.004194', '1.004222'))
    with pytest.raises(ParseError, match='Local procedure variant'):
        portal_identity(detail_page('1.004194.000.00.00.H01'), DETAIL)
    with pytest.raises(ParseError, match='Missing'):
        portal_identity(b'<div id="root"></div>', DETAIL)


def record(tmp_path, name, raw, url):
    path = tmp_path/name
    path.write_bytes(raw)
    return dict(url=url,raw_path=name,sha256=hashlib.sha256(raw).hexdigest(),fetched_at='2026-10-31T00:00:00Z')


def test_resolution_fetches_complete_matching_page_and_retains_provenance(tmp_path, monkeypatch):
    original = record(tmp_path, 'detail.html', detail_page(), DETAIL)
    complete = record(tmp_path, 'complete.html', RAW, CANONICAL)
    monkeypatch.setattr(analysis, 'ROOT', tmp_path)
    calls = []
    def fetch(url, folder):
        calls.append((url, folder))
        return complete
    monkeypatch.setattr(analysis, 'fetch', fetch)
    acquisition = []
    source, parsed, sections, issues = analysis.read_primary(original, acquisition)
    assert calls == [(CANONICAL, 'raw')]
    assert parsed['code'] == '1.004194'
    assert parsed['source_url'] == CANONICAL
    assert len(parsed['requirements']) == 9
    assert 'Trình tự thực hiện' in sections
    assert acquisition[0]['resolved_from'] == DETAIL
    assert source == complete


def test_resolution_rejects_changed_procedure_instead_of_importing_it(tmp_path, monkeypatch):
    original = record(tmp_path, 'detail.html', detail_page(), DETAIL)
    wrong = record(tmp_path, 'wrong.html', RAW.replace(b'1.004194', b'1.004222'), CANONICAL)
    monkeypatch.setattr(analysis, 'ROOT', tmp_path)
    monkeypatch.setattr(analysis, 'fetch', lambda *a: wrong)
    with pytest.raises(ParseError):
        analysis.read_primary(original, [])


def test_same_code_with_updated_title_keeps_both_titles_and_uses_complete_page(tmp_path, monkeypatch):
    original = record(tmp_path, 'detail.html', detail_page(), DETAIL)
    soup = BeautifulSoup(RAW.decode('utf-8'), 'html.parser')
    next(h for h in soup.select('h1.main-title') if h.get_text(strip=True)).string = 'Đăng ký tạm trú (cập nhật)'
    updated = str(soup).encode('utf-8')
    complete = record(tmp_path, 'updated.html', updated, CANONICAL)
    monkeypatch.setattr(analysis, 'ROOT', tmp_path)
    monkeypatch.setattr(analysis, 'fetch', lambda *a: complete)
    acquisition = []
    _, parsed, _, _ = analysis.read_primary(original, acquisition)
    assert parsed['name'] == 'Đăng ký tạm trú (cập nhật)'
    assert acquisition[0]['input_name'] == 'Đăng ký tạm trú'
    assert acquisition[0]['resolved_name'] == parsed['name']
    assert acquisition[0]['title_changed'] is True


def test_url_file_batch_deduplicates_continues_after_failure_and_exits_nonzero(tmp_path, monkeypatch, capsys):
    indexed = []
    monkeypatch.setattr(analysis, 'publish_imports', lambda: indexed.append(True))
    path = tmp_path/'urls.txt'
    path.write_text('# Procedures\n'+DETAIL+'\n\n'+CANONICAL+'\n'+DETAIL+'\n', encoding='utf-8-sig')
    monkeypatch.setattr('sys.argv', ['ingest', '--urls-file', str(path)])
    calls = []
    def run(url, *args):
        calls.append(url)
        if url == DETAIL:
            raise RuntimeError('Source unavailable')
        return dict(status='needs_review',code='1.004194')
    monkeypatch.setattr(analysis, 'run', run)
    with pytest.raises(SystemExit) as error:
        analysis.main()
    assert error.value.code == 1
    assert calls == [DETAIL, CANONICAL]
    assert indexed == [True]
    assert 'Source unavailable' in capsys.readouterr().out


def test_batch_rejects_invalid_url_before_any_ingestion(monkeypatch):
    monkeypatch.setattr('sys.argv', ['ingest', CANONICAL, 'https://evil.test/'])
    monkeypatch.setattr(analysis, 'run', lambda *a: pytest.fail('Should validate first'))
    with pytest.raises(SystemExit) as error:
        analysis.main()
    assert error.value.code == 2


def test_resume_skips_active_success_without_fetching(monkeypatch):
    indexed = []
    monkeypatch.setattr(analysis, 'publish_imports', lambda: indexed.append(True))
    class Result:
        def scalar(self): return '1.004194'
    class Connection:
        def execute(self, *a, **k): return Result()
    class Engine:
        @contextmanager
        def connect(self): yield Connection()
    monkeypatch.setattr(analysis, 'engine', lambda: Engine())
    monkeypatch.setattr('sys.argv', ['ingest', '--resume', DETAIL])
    monkeypatch.setattr(analysis, 'run', lambda *a: pytest.fail('Already imported'))
    analysis.main()
    assert indexed == [True]


def test_index_failure_reports_failure_without_discarding_successful_import(monkeypatch, capsys, caplog):
    monkeypatch.setattr('sys.argv', ['ingest', DETAIL])
    monkeypatch.setattr(analysis, 'run', lambda *a: dict(code='1.004194',status='blocked'))
    def unavailable(): raise RuntimeError('Embedding service unavailable')
    monkeypatch.setattr(analysis,'publish_imports',unavailable)
    with pytest.raises(SystemExit) as exc:
        analysis.main()
    assert exc.value.code==1
    assert '1.004194' in capsys.readouterr().out
    assert 'Procedures were saved' in caplog.text and '--resume' in caplog.text


def test_resuming_unchanged_index_preserves_calibrated_threshold(monkeypatch):
    from api import rag_index
    published=[]
    monkeypatch.setattr(rag_index,'build',lambda:'same-release')
    monkeypatch.setattr(rag_index,'status',lambda:[{'id':'same-release','min_similarity':0.8}])
    monkeypatch.setattr(rag_index,'work',lambda *a,**k:0)
    monkeypatch.setattr(rag_index,'publish',lambda r,minimum:published.append((r,minimum)))
    analysis.publish_imports()
    assert published==[('same-release',0.8)]


class Database:
    def __init__(self):
        self.statements = []

    @contextmanager
    def begin(self):
        yield self

    connect = begin

    def execute(self, statement, params=None):
        self.statements.append((str(statement), params))
        return self

    def mappings(self):
        return []

    def scalar_one(self):
        return 1


@pytest.mark.parametrize('profile_failure', [False, True])
def test_new_url_ingestion_needs_no_registry_and_only_activates_after_extraction(tmp_path, monkeypatch, profile_failure):
    source = record(tmp_path, 'source.html', RAW, CANONICAL)
    db = Database()
    monkeypatch.setattr(analysis, 'ROOT', tmp_path)
    monkeypatch.setattr(analysis, 'engine', lambda: db)
    monkeypatch.setattr(analysis, 'fetch', lambda *a: source)
    monkeypatch.setattr(analysis, 'ingest', lambda *a, **k: (1, True))
    monkeypatch.setattr('api.baseline.ensure', lambda: {'id':'baseline'})
    monkeypatch.setattr('api.baseline.contract', lambda: {'id':'baseline'})
    monkeypatch.setattr(analysis, 'analyse_file', lambda *a, **k: (_ for _ in ()).throw(ValueError('No form rendering in test')))
    exports = []
    monkeypatch.setattr('api.storage.export_procedure', exports.append)
    def extract(*args):
        if profile_failure:
            raise ValueError('Profile validation failed')
        return dict(profile=dict(aliases=[],example_requests=[]),sources=[],output_sha256='0'*64,validation={})
    monkeypatch.setattr('api.profiles.extract', extract)
    report = analysis.run(CANONICAL)
    assert not (tmp_path/'candidates.yaml').exists()
    assert report['input_url'] == CANONICAL
    assert (report['status'] == 'failed') == profile_failure
    activation = [s for s, _ in db.statements if 'SET active=true' in s]
    assert bool(activation) == (not profile_failure)
    assert exports == ([] if profile_failure else ['1.004194'])
    assert json.loads((tmp_path/'data/_store/runs'/f'{report["run_id"]}.json').read_text(encoding='utf-8'))['status'] == report['status']


def test_export_index_includes_active_url_imports_without_yaml(tmp_path, monkeypatch):
    from api import storage
    folder = tmp_path/'data/procedures/1.004194'
    folder.mkdir(parents=True)
    (folder/'procedure.json').write_text(json.dumps(dict(name='Đăng ký tạm trú',source_url=CANONICAL)), encoding='utf-8')
    (folder/'README.md').write_text('Source: '+CANONICAL, encoding='utf-8')
    db = Database()
    db.scalars = lambda: ['1.004194']
    monkeypatch.setattr(storage, 'ROOT', tmp_path)
    monkeypatch.setattr(storage, 'engine', lambda: db)
    storage.export_index()
    assert 'Đăng ký tạm trú' in (tmp_path/'data/README.md').read_text(encoding='utf-8')
    assert not (tmp_path/'candidates.yaml').exists()
