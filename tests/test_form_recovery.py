import hashlib
from api import form_recovery as recovery


def candidate(tmp_path):
    path=tmp_path/'data/forms/_objects/sample/blank.pdf'
    path.parent.mkdir(parents=True)
    path.write_bytes(b'%PDF-test')
    return dict(record=dict(raw_path=path.relative_to(tmp_path).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest()),
                matches=[dict(procedure_code='1.004194',source_url='https://example.gov.vn/form',label='CT01.doc')])


def test_official_copy_requires_exact_procedure_url_and_label(tmp_path,monkeypatch):
    monkeypatch.setattr(recovery,'ROOT',tmp_path)
    item=candidate(tmp_path)
    attachment=dict(url='https://example.gov.vn/form',label='CT01.doc')
    assert recovery.choose_copy('1.004194',attachment,[item])==item
    assert recovery.choose_copy('1.004222',attachment,[item]) is None
    assert recovery.choose_copy('1.004194',{**attachment,'label':'CT02.doc'},[item]) is None
    assert recovery.choose_copy('1.004194',{**attachment,'url':'https://example.gov.vn/new'},[item]) is None


def test_ambiguous_unreviewed_or_corrupt_copy_is_not_associated(tmp_path,monkeypatch):
    monkeypatch.setattr(recovery,'ROOT',tmp_path)
    item=candidate(tmp_path)
    attachment=dict(url='https://example.gov.vn/form',label='CT01.doc')
    assert recovery.choose_copy('1.004194',attachment,[item,item]) is None
    assert recovery.choose_copy('1.004194',attachment,[{**item,'candidate_only':True}]) is None
    (tmp_path/item['record']['raw_path']).write_bytes(b'corrupted')
    assert recovery.choose_copy('1.004194',attachment,[item]) is None
