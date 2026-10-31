import json
import pytest
from fastapi import HTTPException
from api import assistant as a
from api.assistant_documents import document_cards, citation_title
from api.config import ROOT
from api.workflow import Values, schema, validate_partial, preview, filled_pages


def fictional_example():
    return dict(fictional=True,values=json.loads((ROOT/'tests/fixtures/na5-example.json').read_text(encoding='utf-8')))


def sample(code='1.001146', condition=None):
    def fact(value):
        return dict(value=value,status='supported',source_refs=[dict(source_id='primary',quote='NA5 required')])
    name=fact('Tờ khai NA5')
    return a.Retrieval(procedure_code=code, sources=[a.Source(id='s1',title='Procedure | primary | source',
        url='https://example.test/official',text='NA5 required. Vietnamese sponsor relationship evidence.')],
        profile={'required_documents':[dict(name=name,originals=fact('1'),copies=fact('0'),
            required_when=condition or dict(operator='true',source_refs=name['source_refs']))]})


def test_form_card_has_server_owned_urls_and_real_template_identity():
    cards=document_cards(sample(),'What documents do I need?')
    form=cards[0].form
    assert form.schema_url=='/documents/na5-provincial-stay-extension/schema'
    assert form.template_version==schema()['template_version']
    assert form.review_status=='draft' and form.download_available is False
    assert cards[0].originals==1 and cards[0].copies==0


def test_follow_up_keeps_verified_document_panel(monkeypatch):
    monkeypatch.setattr(a,'generate',lambda *args:(a.Generated(status='needs_clarification',
        answer='NA5 is listed. [s1] Is your sponsor an organisation?',source_ids=['s1']),'test'))
    result=a.chat(a.ChatRequest(message='What documents do I need?',procedure_code='1.001146'),
        retriever=lambda request:sample())
    assert result.status=='needs_clarification' and result.documents[0].form.form_id=='NA5'


def test_shared_name_does_not_attach_workflow_to_another_procedure():
    assert document_cards(sample('1.003326'),'Show NA5')[0].form is None


def test_unverified_quotes_never_become_document_cards():
    evidence=sample()
    evidence.profile['required_documents'][0]['name']['source_refs'][0]['quote']='Unverified requirement'
    assert document_cards(evidence,'Documents')==[]


def test_edition_conflict_keeps_form_visible_but_never_resolves_applicability():
    evidence=sample()
    evidence.profile['required_documents'][0]['name']['status']='conflict'
    cards=document_cards(evidence,'Documents')
    assert cards[0].form.applicability=='unresolved'
    assert cards[0].evidence_status=='conflict' and 'accepted edition' in cards[0].description


def test_conditional_family_proof_is_not_mandatory_for_everyone():
    evidence=sample(condition=dict(operator='eq',criterion_key='sponsor_type',values=['vietnamese_citizen_relative'],
        source_refs=[dict(source_id='primary',quote='Vietnamese sponsor relationship evidence.')]))
    evidence.profile['required_documents'][0]['name']=dict(value='Giấy tờ chứng minh quan hệ',status='supported',
        source_refs=[dict(source_id='primary',quote='Vietnamese sponsor relationship evidence.')])
    card=document_cards(evidence,'Documents')[0]
    assert card.requirement=='conditional' and 'If a Vietnamese citizen' in card.condition
    assert card.form is None


def test_unknown_conditions_remain_unconfirmed():
    cards=document_cards(sample(condition=dict(operator='eq',criterion_key='unreviewed',values=['yes'],source_refs=[])),'Documents')
    assert cards[0].requirement=='unconfirmed' and cards[0].condition


def test_vietnamese_checklist_preserves_source_references():
    evidence=sample()
    cards=document_cards(evidence,'Tôi cần chuẩn bị giấy tờ gì?')
    assert cards[0].title=='Tờ khai NA5' and cards[0].source_ids==['s1']


def test_partial_values_are_validated_without_fabricating_missing_data():
    result=validate_partial(Values(values={'applicant_full_name':'fictional person'},template_version=schema()['template_version']))
    assert result['values']['applicant_full_name']=='FICTIONAL PERSON'
    assert result['values']['passport_number']==''
    assert result['ready_for_preview'] is False
    assert any(f['id']=='passport_number' for f in result['missing_fields'])


@pytest.mark.parametrize('values',[{'invented_field':'anything'},{'birth_date':'2026-02-31'},
                                  {'request_type':'visa_issuance'},{'passport_number':'X'*300}])
def test_partial_validation_rejects_invalid_field_changes(values):
    with pytest.raises(HTTPException) as error: validate_partial(Values(values=values))
    assert error.value.status_code==422


def test_stale_template_rejected_for_validation_and_preview():
    for operation in (validate_partial,preview):
        with pytest.raises(HTTPException) as error:operation(Values(values={},template_version='0'*64))
        assert error.value.status_code==409


def test_fictional_fixture_is_complete_and_previewable():
    data=fictional_example()
    assert data['fictional'] is True
    request=Values(values=data['values'],template_version=schema()['template_version'])
    assert validate_partial(request)['ready_for_preview'] is True
    assert preview(request).body.startswith(b'%PDF')


def test_dossier_count_is_submission_guidance_not_an_extra_document():
    evidence=sample()
    row=evidence.profile['required_documents'][0]
    row['name']['value']='01 bộ hồ sơ; không phải giấy tờ riêng'
    card=document_cards(evidence,'Documents')[0]
    assert card.kind=='submission_instruction' and card.title=='One complete set'


def test_page_previews_keep_all_pages_and_review_token():
    import base64
    request=Values(values=fictional_example()['values'],template_version=schema()['template_version'])
    response=filled_pages(request)
    pages=json.loads(response.body)['pages']
    assert len(pages)==3 and [p['page_number'] for p in pages]==[1,2,3]
    assert all(base64.b64decode(p['image_data_url'].split(',',1)[1]).startswith(b'\x89PNG') for p in pages)
    assert response.headers['Cache-Control']=='no-store' and response.headers['X-Review-Token']


def test_english_cards_and_citations_do_not_leak_untranslated_extraction_text():
    evidence=sample()
    evidence.profile['required_documents'][0]['name']['value']='Một câu tiếng Việt chưa được dịch'
    card=document_cards(evidence,'Which documents do I need?')[0]
    assert card.title=='Additional requirement — needs confirmation'
    assert 'Vietnamese' not in citation_title(evidence.sources[0],'1.001146','Help me')
