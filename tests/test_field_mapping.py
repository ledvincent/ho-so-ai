import copy
import json
import pytest
from api import field_mapping as fm


def test_incomplete_response_preserves_failure_reason(tmp_path, monkeypatch):
    import json
    import httpx
    import pytest
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    data = dict(id='resp_test', model='test-model', status='incomplete',
                incomplete_details={'reason': 'max_output_tokens'},
                usage={'output_tokens': 24000})
    monkeypatch.setattr(fm.httpx, 'post', lambda *a, **kw: httpx.Response(
        200, json=data, request=httpx.Request('POST', 'https://api.openai.com/v1/responses')))
    with pytest.raises(ValueError, match='reason=max_output_tokens'):
        fm.invoke('prompt', [], {}, 'openai', 'test-model', 'high', tmp_path)
    saved = json.loads(next(tmp_path.glob('response-metadata-*.json')).read_text())
    assert saved['usage'] == data['usage']
    assert saved['incomplete_details'] == data['incomplete_details']
    assert 'test-key' not in json.dumps(saved)


def test_output_limit_retry_uses_larger_budget_without_accepting_partial_json(tmp_path, monkeypatch):
    import httpx
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    limits = []
    def post(*args, **kwargs):
        limits.append(kwargs['json']['max_output_tokens'])
        data = dict(id='resp_test',model='test-model',status='completed',output=[
            dict(type='message',content=[dict(type='output_text',text='{"complete":true}')])])
        if len(limits)==1:
            data.update(status='incomplete',incomplete_details={'reason':'max_output_tokens'})
        return httpx.Response(200,json=data,request=httpx.Request('POST','https://api.openai.com/v1/responses'))
    monkeypatch.setattr(fm.httpx,'post',post)
    result, metadata = fm.invoke('prompt',[],{},'openai','test-model','medium',tmp_path)
    assert result == {'complete':True}
    assert limits == [fm.MODEL_OUTPUT_TOKENS,fm.MODEL_RETRY_OUTPUT_TOKENS]
    assert metadata['max_output_tokens'] == limits[-1]
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
    with pytest.raises(ValueError,match='Unaccounted|no measured placement'):fm.validate_mapping(result,measured)


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
