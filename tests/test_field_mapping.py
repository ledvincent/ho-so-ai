import copy
import json
import pytest
from api import field_mapping as fm
from api.config import ROOT


@pytest.fixture
def mapped():
    data=json.loads((ROOT/'data/forms/NA5/model-run.json').read_text(encoding='utf-8'))
    return data['result'],data['measured']


def test_all_real_na5_anchors_accounted_for(mapped):
    result,measured=mapped
    fm.validate_mapping(result,measured)
    assert len(measured['anchors'])>=57


def test_missing_anchor_rejected(mapped):
    result,measured=mapped
    result['fields'][0]['placements']=[]
    with pytest.raises(ValueError,match='Unaccounted'):fm.validate_mapping(result,measured)


def test_reused_anchor_rejected(mapped):
    result,measured=mapped
    result['fields'][1]['placements']=copy.deepcopy(result['fields'][0]['placements'])
    with pytest.raises(ValueError,match='reused'):fm.validate_mapping(result,measured)


def test_date_components_are_explicit(mapped):
    result,measured=mapped
    field=next(f for f in result['fields'] if f['type']=='date')
    field['placements'][0]['component']='year'
    with pytest.raises(ValueError,match='Date requires'):fm.validate_mapping(result,measured)


def test_cache_reuses_form_across_procedures(tmp_path,monkeypatch,mapped):
    result,measured=mapped
    monkeypatch.setattr(fm,'ROOT',tmp_path)
    pdf=tmp_path/'blank.pdf';pdf.write_bytes(b'fixture geometry')
    monkeypatch.setattr(fm,'evidence',lambda *_:(measured,[]))
    calls=[]
    def invoke(*args):
        calls.append(args)
        return result,{'provider':'openai','model':'test-model'}
    monkeypatch.setattr(fm,'invoke',invoke)
    a=fm.map_form(pdf,'a'*64,context='Procedure A',provider='openai')
    b=fm.map_form(pdf,'a'*64,context='Procedure B',provider='openai')
    assert len(calls)==1 and a['input_fingerprint']==b['input_fingerprint']
    pdf.write_bytes(b'different geometry')
    fm.map_form(pdf,'a'*64,context='Procedure B',provider='openai')
    assert len(calls)==2
