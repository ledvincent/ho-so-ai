import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import SQLAlchemyError

from api.db import get_procedure
from api.search import search
from api.context import context
from api.config import engine
from api.config import ROOT
from fastapi.responses import FileResponse
import hashlib
import re
from sqlalchemy import text

app = FastAPI(title="Hồ Sơ AI", version="0.1.0")
from api.workflow import router as workflow_router
app.include_router(workflow_router)
from api.form_workflows import router as document_router
app.include_router(document_router)
from api.assistant import router as assistant_router
app.include_router(assistant_router)


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=1000)

    @field_validator("query")
    @classmethod
    def clean(cls, value):
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Enter a procedure request")
        return value


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/procedures/{code}")
def procedure(code: str):
    try:
        result = get_procedure(code)
    except SQLAlchemyError:
        raise HTTPException(503, "Database unavailable") from None
    if not result:
        raise HTTPException(404, "Procedure not covered")
    # Routing can identify this record; factual evidence still requires readiness.
    return result


@app.get('/procedures/{code}/profile')
def procedure_profile(code: str):
    result=procedure(code)
    profile=result.get('structured_profile')
    if not profile:raise HTTPException(404,'Structured profile has not been extracted')
    with engine().connect() as db:
        batch=db.execute(text("SELECT id,report FROM catalog_batch WHERE baseline_id=:baseline AND status='complete' ORDER BY created_at DESC LIMIT 1"),dict(baseline=profile['baseline_id'])).mappings().first()
        member=next((p for p in batch['report']['procedures'] if p['code']==code),None) if batch else None
        # A later single-procedure run under the same contract must not inherit
        # comparisons against old evidence merely because the baseline matches.
        current=member and str(member['run_id'])==str(profile['run_id'])
        related=[dict(r) for r in db.execute(text('SELECT left_code,right_code,result FROM procedure_comparison WHERE batch_id=:batch AND (left_code=:code OR right_code=:code)'),dict(batch=batch['id'],code=code)).mappings()] if current else []
        comparison_sources=[]
        if current:
            for item in batch['report']['procedures']:
                sources=db.execute(text('SELECT sources FROM procedure_profile WHERE run_id=:run AND baseline_id=:baseline'),dict(run=item['run_id'],baseline=profile['baseline_id'])).scalar_one()
                comparison_sources.extend({**s,'source_id':item['code']+'/'+s['source_id']} for s in sources)
    return {**profile,'related_procedures':related,'comparison_sources':comparison_sources,'usage':'Validated extraction draft; citations verify source membership, not legal currency. Generated routing phrases are not factual evidence.'}


@app.post("/search")
def find(request: SearchRequest):
    try:
        return search(request.query)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from None
    except (httpx.HTTPError, ValueError, KeyError, SQLAlchemyError):
        raise HTTPException(503, "Retrieval unavailable") from None


@app.post('/procedures/{code}/context')
def assistant_context(code: str, request: SearchRequest):
    try:
        return context(code,request.query)
    except LookupError as exc:
        raise HTTPException(404,str(exc)) from None
    except RuntimeError as exc:
        raise HTTPException(409,str(exc)) from None
    except SQLAlchemyError:
        raise HTTPException(503,'Database unavailable') from None


@app.get('/forms/{sha256}/analysis')
def form_analysis(sha256: str):
    try:
        with engine().connect() as db:
            form = db.execute(text('SELECT sha256,review_status,pdf_path,analysis_issues,revision_reference,issued_on,effective_from,source_metadata,fields_json,mapping_metadata FROM form WHERE sha256=:sha'),dict(sha=sha256)).mappings().first()
            if not form:
                raise HTTPException(404,'Form not downloaded')
            fields = db.execute(text('SELECT * FROM form_field WHERE form_sha256=:sha ORDER BY page,field_id'),dict(sha=sha256)).mappings()
            return {**dict(form),'fields':[dict(f) for f in fields]}
    except SQLAlchemyError:
        raise HTTPException(503,'Database unavailable') from None


@app.get('/forms/{sha256}/original')
def original_form(sha256: str):
    if not re.fullmatch('[a-f0-9]{64}',sha256):
        raise HTTPException(404,'Form not downloaded')
    try:
        with engine().connect() as db:
            stored=db.execute(text('SELECT raw_path FROM form WHERE sha256=:sha'),dict(sha=sha256)).scalar()
    except SQLAlchemyError:
        raise HTTPException(503,'Database unavailable') from None
    if not stored:raise HTTPException(404,'Form not downloaded')
    path=(ROOT/stored).resolve()
    if not path.is_relative_to((ROOT/'data/forms').resolve()) or not path.is_file():
        raise HTTPException(409,'Stored original unavailable')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=sha256:
        raise HTTPException(409,'Stored original failed integrity check')
    return FileResponse(path,filename=path.name,headers={'ETag':'"'+sha256+'"'})
