from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import pytest
from api import documents


def test_same_name_different_bytes_retains_exact_versions(tmp_path, monkeypatch):
    monkeypatch.setattr(documents,'ROOT',tmp_path)
    first=documents.store_document(b'%PDF-first','https://example.invalid/NA5.pdf')
    second=documents.store_document(b'%PDF-second','https://example.invalid/NA5.pdf')
    assert first['raw_path']!=second['raw_path']
    for record in (first,second):
        assert record['sha256'][:12] in record['stored_filename']
        assert hashlib.sha256((tmp_path/record['raw_path']).read_bytes()).hexdigest()==record['sha256']


def test_identical_bytes_different_names_and_concurrent_downloads(tmp_path, monkeypatch):
    monkeypatch.setattr(documents,'ROOT',tmp_path)
    with ThreadPoolExecutor(max_workers=5) as pool:
        results=list(pool.map(lambda n:documents.store_document(b'%PDF-same',f'https://example.invalid/form{n}.pdf'),range(5)))
    assert len({r['raw_path'] for r in results})==1
    assert len(list(tmp_path.rglob('*.pdf')))==1
    assert len({r['original_filename'] for r in results})==5


def test_html_error_is_not_stored_as_form(tmp_path, monkeypatch):
    monkeypatch.setattr(documents,'ROOT',tmp_path)
    with pytest.raises(ValueError):documents.store_document(b'<html>503</html>','https://example.invalid/NA5.doc')
    assert not list(tmp_path.rglob('*.doc'))


def test_windows_deleted_lock_race_is_retried(tmp_path, monkeypatch):
    monkeypatch.setattr(documents,'ROOT',tmp_path)
    mkdir=Path.mkdir
    calls=[]
    def race(path,*args,**kwargs):
        if path.name=='.write-lock' and not calls:
            calls.append(True)
            exc=PermissionError('Directory deletion pending')
            exc.winerror=5
            raise exc
        return mkdir(path,*args,**kwargs)
    monkeypatch.setattr(Path,'mkdir',race)
    result=documents.store_document(b'%PDF-race','https://example.invalid/form.pdf')
    assert (tmp_path/result['raw_path']).read_bytes()==b'%PDF-race'
    assert not list(tmp_path.rglob('.write-lock'))


def test_misleading_extension_and_path_filename_are_safe(tmp_path, monkeypatch):
    monkeypatch.setattr(documents,'ROOT',tmp_path)
    record=documents.store_document(b'PK\x03\x04test','https://example.invalid/NA5.doc', '../../NA5.doc')
    assert record['stored_filename'].endswith('.docx')
    assert (tmp_path/record['raw_path']).resolve().is_relative_to(tmp_path.resolve())
