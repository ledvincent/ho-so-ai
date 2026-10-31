import json
import pymupdf
import pytest
from fastapi import HTTPException
from api import na5
from api.config import ROOT
from api.workflow import Values,Download,preview,download
from scripts.review_na5 import family_example

@pytest.fixture
def values():
    return json.loads((ROOT/'tests/fixtures/na5-example.json').read_text(encoding='utf-8'))

def test_all_pages_kept_and_unicode_values_written(values):
    raw=na5.render(values)
    with pymupdf.open(stream=raw,filetype='pdf') as pdf:
        assert len(pdf)==3
        body='\n'.join(p.get_text() for p in pdf)
        assert 'ÉLODIE EXEMPLE' in body
        assert '123 Đường Ví Dụ, Hà Nội' in body
        assert 'TEST000123' in body
        assert 'Fictional example' in body
        assert 'TEMPLATE REVIEW DRAFT' in body
        assert 'According to the provisions' in body
        assert 'Temporary Resident Card' in pdf[2].get_text()

def test_sponsor_is_not_filled_from_applicant():
    raw=na5.render(family_example())
    with pymupdf.open(stream=raw,filetype='pdf') as pdf:
        assert 'PERSONNE EXEMPLE' in pdf[0].get_text()
        assert 'TEST-TRC-001' in '\n'.join(p.get_text() for p in pdf)
        assert 'ÉLODIE EXEMPLE' not in pdf[1].get_text()

@pytest.mark.parametrize('key,value',[('birth_date','2026-02-30'),('extension_until','2031-01-01'),('sex','unknown'),('passport_number','x'*100),('organisation_name','x'*100)])
def test_invalid_or_overflowing_values_rejected(values,key,value):
    values[key]=value
    with pytest.raises(ValueError):na5.render(values)

def test_applicable_sponsor_fields_required(values):
    values['host_type']='family'
    with pytest.raises(ValueError):na5.validate(values)

def test_preview_confirmation_bound_to_values(values):
    t=na5.token(values)
    na5.verify_token(values,t)
    values['reason']='Changed after preview'
    with pytest.raises(ValueError):na5.verify_token(values,t)


def test_current_nationality_stays_beside_its_own_label(values):
    values['birth_nationality']='France'
    values['current_nationality']='Canada'
    with pymupdf.open(stream=na5.render(values),filetype='pdf') as pdf:
        answer=pdf[0].search_for('Canada')[0]
        label=pdf[0].search_for('5.')[0]
        assert abs(answer.y0-label.y0)<8 and answer.x0>label.x0


def test_vietnamese_sponsor_does_not_require_residence_card():
    values=family_example()
    values['sponsor_kind']='vietnamese_citizen'
    for key in list(values):
        if key.startswith('sponsor_card_'):del values[key]
    assert na5.render(values)


def test_extension_workflow_rejects_visa_branch(values):
    values['request_type']='visa_issuance'
    with pytest.raises(ValueError,match='only supports'):na5.render(values)

def test_download_requires_template_review_and_exact_preview(values,monkeypatch):
    response=preview(Values(values=values))
    assert response.media_type=='application/pdf'
    t=response.headers['X-Review-Token']
    with pytest.raises(HTTPException) as error:
        download(Download(values=values,review_token=t,confirmed=True))
    assert error.value.status_code==409
    original=na5.spec()
    monkeypatch.setattr(na5,'spec',lambda:{**original,'review_status':'reviewed'})
    with pytest.raises(HTTPException):download(Download(values=values,review_token=t,confirmed=False))
    response=download(Download(values=values,review_token=t,confirmed=True))
    assert response.headers['content-disposition'].endswith('"NA5-filled.pdf"')
    with pymupdf.open(stream=response.body,filetype='pdf') as pdf:
        assert len(pdf)==3 and 'TEMPLATE REVIEW DRAFT' not in pdf[0].get_text()
