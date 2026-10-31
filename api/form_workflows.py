"""Document-specific schema, validation and PDF routes for all installed forms."""
from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import Response,FileResponse,JSONResponse
from pydantic import BaseModel,ConfigDict,Field
from api.config import ROOT
from api import form_engine as engine,form_registry as registry
from api.workflow import Values,Download

router=APIRouter(tags=['documents'])


class FormField(BaseModel):
    model_config=ConfigDict(extra='allow')
    id:str
    label:str
    type:str
    required:bool=False
    when:dict[str,str]=Field(default_factory=dict)
    options:list[str]|None=None
    owner:str|None=None
    group:str|None=None
    manual:bool=False
    hidden:bool=False
    inactive:bool=False
    max_length:int|None=None


class DocumentSchema(BaseModel):
    document_id:str
    procedure_code:str
    form_id:str
    name:str
    revision:str
    effective_from:str|None
    review_status:str
    applicability:str
    download_available:bool
    template_version:str
    template_sha256:str
    page_count:int
    fields:list[FormField]
    fixed_values:dict[str,str]
    date_order:list[list[str]]


def document(document_id:str):
    try:return registry.get_document(document_id)
    except LookupError as exc:raise HTTPException(404,str(exc)) from None
    except (ValueError,OSError,KeyError):raise HTTPException(409,'Installed document configuration is unavailable') from None


def version(doc,request=None):
    try:current=doc.version()
    except (ValueError,OSError):raise HTTPException(409,'Template integrity check failed') from None
    if request and request.template_version and request.template_version!=current:
        raise HTTPException(409,'The template changed. Reopen the document and review the fields again.')
    return current


@router.get('/procedures/{procedure_code}/documents')
def procedure_documents(procedure_code:str):
    return dict(documents=[doc.action() for doc in registry.for_procedure(procedure_code)])


@router.get('/documents/{document_id}/schema',response_model=DocumentSchema,response_model_exclude_unset=True)
def schema(doc=Depends(document)):
    version(doc)
    return doc.schema()


@router.get('/documents/{document_id}/template')
def template(doc=Depends(document)):
    version(doc)
    return FileResponse(ROOT/doc.mapping['pdf_path'],media_type='application/pdf',headers={'Cache-Control':'no-store'})


@router.get('/documents/{document_id}/template-pages')
def template_pages(doc=Depends(document)):
    current=version(doc)
    return JSONResponse(dict(pages=engine.page_previews((ROOT/doc.mapping['pdf_path']).read_bytes()),template_version=current),
                        headers={'Cache-Control':'no-store'})


@router.post('/documents/{document_id}/validate')
def validate(request:Values,doc=Depends(document)):
    current=version(doc,request)
    try:clean=engine.validate(request.values,doc.mapping,partial=True)
    except ValueError as exc:raise HTTPException(422,str(exc)) from None
    missing=[dict(id=f['id'],label=f['label']) for f in doc.mapping['fields']
             if engine.active(f,clean) and f.get('required') and not clean.get(f['id'])]
    return dict(values=clean,missing_fields=missing,ready_for_preview=not missing,template_version=current,
                note='PDF preview also checks character support and printed space.')


@router.post('/documents/{document_id}/preview')
def preview(request:Values,doc=Depends(document)):
    version(doc,request)
    try:
        payload=engine.render(request.values,doc.mapping,draft=doc.mapping['review_status']!='reviewed')
        return Response(payload,media_type='application/pdf',headers={'Cache-Control':'no-store',
            'X-Review-Token':engine.token(request.values,doc.mapping)})
    except ValueError as exc:raise HTTPException(422,str(exc)) from None


@router.post('/documents/{document_id}/preview-pages')
def preview_pages(request:Values,doc=Depends(document)):
    response=preview(request,doc)
    return JSONResponse(dict(pages=engine.page_previews(response.body),template_version=version(doc)),
                        headers={'Cache-Control':'no-store','X-Review-Token':response.headers['X-Review-Token']})


@router.post('/documents/{document_id}/download')
def download(request:Download,doc=Depends(document)):
    version(doc,request)
    if doc.mapping['review_status']!='reviewed':
        raise HTTPException(409,'Template field map awaits human review. Use the fictional-data preview for review.')
    if not request.confirmed:raise HTTPException(422,'Review the preview and confirm the information first')
    try:
        engine.verify_token(request.values,request.review_token,doc.mapping)
        payload=engine.render(request.values,doc.mapping,draft=False)
        return Response(payload,media_type='application/pdf',headers={'Cache-Control':'no-store',
            'Content-Disposition':f'attachment; filename="{doc.id}-filled.pdf"'})
    except ValueError as exc:raise HTTPException(422,str(exc)) from None
