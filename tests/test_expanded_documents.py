import json

import pymupdf
import pytest
from fastapi import HTTPException
from api.config import ROOT
from api import form_registry, form_workflows, form_engine
from api.field_mapping import empty_cells, extra_anchors
from api.workflow import Values, Download


@pytest.mark.parametrize('document_id,fixture,date_text',[
    ('marriage-declaration-1-000894','marriage-example.json','01/02/1994'),
    ('ct01-1-004194','ct01-example.json',None),
])
def test_real_recovered_forms_validate_preview_and_preserve_review_gate(document_id,fixture,date_text):
    doc=form_registry.get_document(document_id)
    values=json.loads((ROOT/'tests/fixtures'/fixture).read_text(encoding='utf8'))
    request=Values(values=values,template_version=doc.version())
    assert form_workflows.validate(request,doc)['ready_for_preview']
    response=form_workflows.preview(request,doc)
    with pymupdf.open(stream=response.body,filetype='pdf') as pdf:
        assert len(pdf)==2
        content=''.join(page.get_text() for page in pdf)
        assert 'FICTIONAL DATA ONLY' in content and 'EXAMPLE NGUYEN AN' in content
        if date_text: assert date_text in content
    token=response.headers['X-Review-Token']
    form_engine.verify_token(values,token,doc.mapping)
    with pytest.raises(HTTPException) as exc:
        form_workflows.download(Download(values=values,template_version=doc.version(),review_token=token,confirmed=True),doc)
    assert exc.value.status_code==409


def test_table_fields_character_boxes_and_raster_checkboxes_are_measured():
    marriage=form_registry.get_document('marriage-declaration-1-000894')
    with pymupdf.open(ROOT/marriage.mapping['pdf_path']) as pdf:
        assert len(empty_cells(pdf[0]))==14
        assert len([a for a in extra_anchors(pdf[0],1) if a['kind']=='image_control'])==2
    copies=next(f for f in marriage.mapping['fields'] if f['id']=='copies_requested')
    assert set(copies['marks'])=={'yes','no'}
    ct01=form_registry.get_document('ct01-1-004194')
    identity=next(f for f in ct01.mapping['fields'] if f['id']=='applicant_personal_identification_number')
    assert len(identity['placements'][0]['boxes'])==12
    signing_date=next(f for f in ct01.mapping['fields'] if f['id']=='declaration_date')
    assert signing_date['manual'] and 'too narrow' in signing_date['manual_reason']
    with pytest.raises(ValueError,match='too long'):
        form_engine.validate({'applicant_personal_identification_number':'0'*13},ct01.mapping,partial=True)


def test_named_form_binding_is_procedure_specific_and_quote_checked():
    title='Tờ khai đăng ký kết hôn'
    assert form_registry.for_requirement('1.000894',title,[title]).entry['form_id']=='marriage-declaration'
    assert form_registry.for_requirement('1.001146',title,[title]) is None
    assert form_registry.for_requirement('1.000894',title,['Unsupported quote']) is None


def test_shared_ct01_has_distinct_versions_for_each_procedure():
    first=form_registry.get_document('ct01-1-004194')
    second=form_registry.get_document('ct01-1-004222')
    assert first.mapping['pdf_sha256']==second.mapping['pdf_sha256']
    assert first.version()!=second.version()
    token=form_engine.token({},first.mapping)
    with pytest.raises(ValueError):form_engine.verify_token({},token,second.mapping)
