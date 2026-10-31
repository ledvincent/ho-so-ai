import hashlib
import json
from zipfile import ZipFile
import pytest
from scripts.restore_backend_data import verified_files, restore


def bundle(root, files):
    folder=root/'data/bootstrap'
    folder.mkdir(parents=True)
    archive=folder/'procedure-data.zip'
    with ZipFile(archive,'w') as z:
        for name,payload in files.items():z.writestr(name,payload)
    manifest=dict(archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                  files={k:hashlib.sha256(v).hexdigest() for k,v in files.items()})
    (folder/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
    return archive


def test_bundle_corruption_and_path_escape_are_rejected(tmp_path):
    archive=bundle(tmp_path,{'procedure-db.dump':b'dump','data/_store/html/example':b'html'})
    assert verified_files(tmp_path)[1]['procedure-db.dump']==b'dump'
    archive.write_bytes(archive.read_bytes()+b'changed')
    with pytest.raises(ValueError,match='checksum'):verified_files(tmp_path)
    other=tmp_path/'escape'
    bundle(other,{'procedure-db.dump':b'dump','data/_store/../../.env':b'bad'})
    with pytest.raises(ValueError,match='path'):verified_files(other)


def test_existing_database_is_not_overwritten(tmp_path):
    calls=[]
    def run(*args,**kwargs):
        calls.append(args)
        return '1' if len(calls)==1 else '12'
    with pytest.raises(ValueError,match='not empty'):
        restore('hoso',{'procedure-db.dump':b'dump','data/_store/html/file':b'html'},run,tmp_path)
    assert all(args[0]=='psql' for args in calls)
    assert not (tmp_path/'data/_store/html/file').exists()


def test_restore_uses_transaction_and_preserves_existing_assets(tmp_path):
    calls=[]
    def run(*args,**kwargs):
        calls.append((args,kwargs))
        return ''
    files={'procedure-db.dump':b'dump','data/_store/html/file':b'html'}
    restore('hoso_test',files,run,tmp_path)
    assert calls[-1][0][0]=='pg_restore' and '--single-transaction' in calls[-1][0]
    assert calls[-1][1]['payload']==b'dump'
    assert (tmp_path/'data/_store/html/file').read_bytes()==b'html'
    calls.clear()
    with pytest.raises(ValueError,match='Existing asset differs'):
        restore('hoso_test',{**files,'data/_store/html/file':b'changed'},run,tmp_path)
    assert not calls
