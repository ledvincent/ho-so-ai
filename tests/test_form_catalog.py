from api import form_catalog as catalog


def form(sha='a',family='CT01',downloads=None,available=True):
    return dict(sha256=sha,family=family,downloads=downloads or [],available=available,
                raw_path=f'data/forms/_objects/{sha}/blank.doc',labels=['CT01'],
                review_status='draft',revision_reference=None)


def test_decorated_form_labels_and_distinct_codes():
    assert catalog.form_codes('Mẫu CT01 _66.doc')=={'CT01'}
    assert catalog.form_codes('CT01A.doc')==set()
    assert catalog.select_local('url','CT01.doc',[form(family='CT010')])['mode']=='not_found'


def test_exact_recorded_url_beats_family_and_preserves_date():
    exact=form('old',downloads=[dict(source_url='url',fetched_at='2025-01-01')])
    result=catalog.select_local('url','CT01.doc',[form('new'),exact])
    assert result['mode']=='stored_exact_url'
    assert result['form']['sha256']=='old'
    assert result['fetched_at']=='2025-01-01'


def test_multiple_versions_are_not_silently_substituted():
    assert catalog.select_local('url','CT01.doc',[form('old'),form('new')])['mode']=='ambiguous'
    assert catalog.select_local('url','CT01.doc',[form(available=False)])['mode']=='not_found'
    result=catalog.select_local('url','Mẫu CT01 _66.doc',[form()])
    assert result['mode']=='stored_family_candidate' and result['fetched_at'] is None


def test_same_url_with_conflicting_downloads_stays_ambiguous():
    downloads=[dict(source_url='url',fetched_at='2025-01-01')]
    assert catalog.select_local('url','CT01.doc',[form('a',downloads=downloads),form('b',downloads=downloads)])['mode']=='ambiguous'


def test_recovery_records_uncertainty_without_new_download_timestamp():
    class DB:
        rowcount=1
        def execute(self,sql,args):
            assert args['method']=='filename_fallback'
            assert args['date'] is None
            assert args['exact'] is False
            return self
    result=catalog.recover_local(DB(),3,{'url':'url','label':'Mẫu CT01 _66.doc'},[form()])
    assert result['version_verified'] is False and result['association_updated'] is True


def test_index_has_all_versions_and_missing_files_without_broken_links(tmp_path,monkeypatch):
    monkeypatch.setattr(catalog,'ROOT',tmp_path)
    original=tmp_path/'data/forms/_objects/old/blank.doc'
    original.parent.mkdir(parents=True)
    original.write_bytes(b'fixture')
    catalog.export_catalog([form('old'),form('new',available=False)])
    output=(tmp_path/'data/forms/index.md').read_text(encoding='utf-8')
    assert '2 stored versions' in output and 'Missing/corrupt' in output
    assert '_objects/old/blank.doc' in output and '_objects/new/blank.doc' not in output
    assert 'Unknown' in output and 'draft' in output
