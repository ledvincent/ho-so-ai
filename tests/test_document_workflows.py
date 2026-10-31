"""A second schema proves that neither transport nor validation assumes NA5 fields."""
import copy
import pytest
from fastapi import HTTPException
from api import form_workflows as routes
from api.workflow import Values
from api.main import app
from api import form_registry as registry,form_engine


@pytest.fixture
def documents(monkeypatch):
    original=registry.get_document('na5-provincial-stay-extension')
    mapping=copy.deepcopy(original.mapping)
    mapping.update(document_id='test-company',form_id='TEST-COMPANY',procedure_code='9.000001',
        fixed_values={},date_order=[],fields=[
            dict(id='company_name',label='Company name',type='text',required=True,max_length=80),
            dict(id='reference',label='Reference',type='text',required=False,max_length=20)])
    # Reuse an existing blank PDF solely for transport tests; never install a fake form.
    second=registry.Document(dict(document_id='test-company',form_id='TEST-COMPANY',
        procedure_code='9.000001',name='Test company document',applicability='unresolved'),mapping)
    records={original.id:original,second.id:second}
    def get(key):
        if key not in records:raise LookupError('Document workflow is not installed')
        return records[key]
    monkeypatch.setattr(registry,'get_document',get)
    monkeypatch.setattr(registry,'entries',lambda:[d.entry for d in records.values()])
    return records


def test_each_document_exposes_its_own_fields_and_actions(documents):
    first=routes.DocumentSchema.model_validate(routes.schema(documents['na5-provincial-stay-extension']))
    second=routes.DocumentSchema.model_validate(routes.schema(documents['test-company']))
    assert len(first.fields)==43
    assert [f.id for f in second.fields]==['company_name','reference']
    assert second.form_id=='TEST-COMPANY' and second.fixed_values=={}
    action=routes.procedure_documents('9.000001')['documents'][0]
    assert action['schema_url']=='/documents/test-company/schema'
    assert action['example_url'] is None
    with pytest.raises(HTTPException) as error:routes.document('uninstalled')
    assert error.value.status_code==404
    assert routes.procedure_documents('9.999999')=={'documents':[]}
    assert '/documents/{document_id}/schema' in app.openapi()['paths']


def test_validation_and_preview_use_selected_document_not_na5(documents):
    second=documents['test-company']
    result=routes.validate(Values(values={}),second)
    assert result['missing_fields']==[dict(id='company_name',label='Company name')]
    request=Values(values={'company_name':'Example company'},template_version=second.version())
    result=routes.validate(request,second)
    assert result['ready_for_preview'] is True
    assert result['values']['company_name']=='Example company'
    assert routes.preview(request,second).headers['content-type']=='application/pdf'
    with pytest.raises(HTTPException) as error:routes.validate(Values(values={'passport_number':'fake'}),second)
    assert error.value.status_code==422
    with pytest.raises(HTTPException) as error:routes.validate(request,documents['na5-provincial-stay-extension'])
    assert error.value.status_code==409
    with pytest.raises(HTTPException) as error:routes.validate(Values(values=request.values),documents['na5-provincial-stay-extension'])
    assert error.value.status_code==422


def test_document_identity_binds_tokens_even_with_identical_fields(documents):
    mapping=documents['test-company'].mapping
    values={'company_name':'Example'}
    token=form_engine.token(values,mapping)
    form_engine.verify_token(values,token,mapping)
    with pytest.raises(ValueError):
        form_engine.verify_token(values,token,{**mapping,'document_id':'different-document'})


def test_chat_card_selects_registered_form_for_its_procedure(documents):
    from api.assistant import Retrieval,Source
    from api.assistant_documents import document_cards
    refs=[dict(source_id='primary',quote='TEST-COMPANY application required')]
    evidence=Retrieval(procedure_code='9.000001',sources=[Source(id='s1',
        title='Test | primary | source',url='https://example.test/document',text=refs[0]['quote'])],
        profile={'required_documents':[dict(name=dict(value='TEST-COMPANY application',status='supported',source_refs=refs),
            required_when=dict(operator='true',source_refs=refs))]})
    card=document_cards(evidence,'What documents do I need?')[0]
    assert card.form.document_id=='test-company'
    assert card.form.schema_url=='/documents/test-company/schema'
