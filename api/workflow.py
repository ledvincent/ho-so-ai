from fastapi import APIRouter,HTTPException
from fastapi.responses import HTMLResponse,Response,FileResponse,JSONResponse
from pydantic import BaseModel,ConfigDict,Field
import json
from api.config import ROOT
from api import na5

router=APIRouter(prefix='/workflows/1.001146')

class Values(BaseModel):
    model_config=ConfigDict(extra='forbid')
    values:dict[str,str]
    template_version:str|None=Field(default=None,pattern=r'^[a-f0-9]{64}$')

class Download(Values):
    review_token:str
    confirmed:bool

@router.get('',response_class=HTMLResponse)
def page():
    return (ROOT/'api/static/na5.html').read_text(encoding='utf-8')

@router.get('/schema')
def schema():
    mapping=na5.spec()
    return dict(procedure_code='1.001146',form_id='NA5',name='Temporary stay extension — provincial level',revision=mapping['revision_reference'],effective_from=mapping['effective_from'],review_status=mapping['review_status'],fields=mapping['fields'],fixed_values=mapping.get('fixed_values',{}),
                template_version=na5.template_digest(mapping),template_sha256=mapping['form_sha256'],download_available=mapping['review_status']=='reviewed',applicability='unresolved')


def check_version(request):
    current=na5.template_digest(na5.spec())
    if request.template_version and request.template_version!=current:
        raise HTTPException(409,'The template changed. Reopen the document and review the fields again.')
    return current


@router.get('/template')
def blank_template():
    mapping=na5.spec()
    na5.template_digest(mapping)
    return FileResponse(ROOT/mapping['pdf_path'],media_type='application/pdf',headers={'Cache-Control':'no-store'})


@router.get('/template-pages')
def blank_pages():
    mapping=na5.spec()
    version=na5.template_digest(mapping)
    return JSONResponse(dict(pages=na5.page_previews((ROOT/mapping['pdf_path']).read_bytes()),template_version=version),
                        headers={'Cache-Control':'no-store'})


@router.get('/example')
def fictional_example():
    return dict(fictional=True,values=json.loads((ROOT/'tests/fixtures/na5-example.json').read_text(encoding='utf-8')))


@router.post('/validate')
def validate_partial(request:Values):
    version=check_version(request)
    try:
        clean=na5.validate(request.values,partial=True)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from None
    mapping=na5.spec()
    missing=[dict(id=f['id'],label=f['label']) for f in mapping['fields']
             if na5.active(f,clean) and f.get('required') and not clean.get(f['id'])]
    return dict(values=clean,missing_fields=missing,ready_for_preview=not missing,template_version=version,
                note='PDF preview also checks character support and printed space.')

@router.post('/preview')
def preview(request:Values):
    check_version(request)
    try:
        payload=na5.render(request.values,draft=na5.spec()['review_status']!='reviewed')
        return Response(payload,media_type='application/pdf',headers={'Cache-Control':'no-store','X-Review-Token':na5.token(request.values)})
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from None


@router.post('/preview-pages')
def filled_pages(request:Values):
    response=preview(request)
    return JSONResponse(dict(pages=na5.page_previews(response.body),template_version=na5.template_digest(na5.spec())),
                        headers={'Cache-Control':'no-store','X-Review-Token':response.headers['X-Review-Token']})

@router.post('/download')
def download(request:Download):
    check_version(request)
    if na5.spec()['review_status']!='reviewed':
        raise HTTPException(409,'Template field map awaits human review. Use the fictional-data preview for review.')
    if not request.confirmed:
        raise HTTPException(422,'Review the preview and confirm the information first')
    try:
        na5.verify_token(request.values,request.review_token)
        payload=na5.render(request.values,draft=False)
        return Response(payload,media_type='application/pdf',headers={'Cache-Control':'no-store','Content-Disposition':'attachment; filename="NA5-filled.pdf"'})
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from None
