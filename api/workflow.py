from fastapi import APIRouter,HTTPException
from fastapi.responses import HTMLResponse,Response
from pydantic import BaseModel,ConfigDict
from api.config import ROOT
from api import na5

router=APIRouter(prefix='/workflows/1.001146')

class Values(BaseModel):
    model_config=ConfigDict(extra='forbid')
    values:dict[str,str]

class Download(Values):
    review_token:str
    confirmed:bool

@router.get('',response_class=HTMLResponse)
def page():
    return (ROOT/'api/static/na5.html').read_text(encoding='utf-8')

@router.get('/schema')
def schema():
    mapping=na5.spec()
    return dict(procedure_code='1.001146',name='Temporary stay extension — provincial level',revision=mapping['revision_reference'],effective_from=mapping['effective_from'],review_status=mapping['review_status'],fields=mapping['fields'],fixed_values=mapping.get('fixed_values',{}))

@router.post('/preview')
def preview(request:Values):
    try:
        payload=na5.render(request.values,draft=na5.spec()['review_status']!='reviewed')
        return Response(payload,media_type='application/pdf',headers={'Cache-Control':'no-store','X-Review-Token':na5.token(request.values)})
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from None

@router.post('/download')
def download(request:Download):
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
