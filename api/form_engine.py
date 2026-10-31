"""Schema-driven PDF validation, rendering and review tokens. No personal data persisted."""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import date
from pathlib import Path

import pymupdf
from api.config import ROOT

FONT_PATH = ROOT/'api/assets/DejaVuSans.ttf'
SECRET = os.getenv('FORM_REVIEW_SECRET','').encode() or secrets.token_bytes(32)


def active(field, values):
    return all(values.get(k)==v for k,v in field.get('when',{}).items()) and not field.get('manual') and not field.get('inactive')


def validate(values, mapping, *, partial=False):
    known = {f['id']:f for f in mapping['fields']}
    if not isinstance(values,dict) or set(values)-set(known):
        raise ValueError('Unknown form fields')
    for key,value in mapping.get('fixed_values',{}).items():
        if key in values and values[key]!=value:
            raise ValueError('This workflow only supports '+value.replace('_',' '))
    values={**mapping.get('fixed_values',{}),**values}
    clean = {}
    for key,field in known.items():
        value = values.get(key,'')
        if not isinstance(value,str):
            raise ValueError(field['label']+': enter text')
        value = value.strip()
        if any(ord(c)<32 and c not in '\n\t' for c in value):
            raise ValueError(field['label']+': unsupported control character')
        if not active(field,values):
            if value:
                raise ValueError(field['label']+': not applicable to the selected case')
            continue
        if not partial and field.get('required') and not value:
            raise ValueError(field['label']+': required')
        if len(value)>field.get('max_length',200):
            raise ValueError(field['label']+': value is too long')
        if value and field['type']=='date':
            try:
                date.fromisoformat(value)
            except ValueError:
                raise ValueError(field['label']+': use YYYY-MM-DD') from None
        if value and field.get('options') and value not in field['options']:
            raise ValueError(field['label']+': choose a listed option')
        if field.get('uppercase'):
            value=value.upper()
        clean[key]=value
    dates = {k:date.fromisoformat(v) for k,v in clean.items() if v and known[k]['type']=='date'}
    for earlier,later in mapping.get('date_order',[]):
        if earlier in dates and later in dates and dates[earlier]>dates[later]:
            raise ValueError(known[earlier]['label']+' must not be after '+known[later]['label'])
    return clean


def template_digest(mapping):
    raw=ROOT/mapping['pdf_path']
    if hashlib.sha256(raw.read_bytes()).hexdigest()!=mapping['pdf_sha256']:
        raise ValueError('Template PDF has changed; field map must be rechecked')
    return hashlib.sha256(json.dumps(mapping,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def render(values, mapping, draft=True):
    template_digest(mapping)
    values=validate(values,mapping)
    font=pymupdf.Font(fontfile=str(FONT_PATH))
    pdf=pymupdf.open(ROOT/mapping['pdf_path'])
    for page in pdf:
        page.insert_font(fontname='FormFont',fontfile=str(FONT_PATH))
    for field in mapping['fields']:
        value=values.get(field['id'],'')
        if not value or not field.get('placements'):
            continue
        pieces=[]
        if field['type']=='date':
            day=date.fromisoformat(value)
            components=dict(day=f'{day.day:02}',month=f'{day.month:02}',year=str(day.year),value=day.strftime('%d/%m/%Y'))
            pieces=[components[p.get('component',key)] for p,key in zip(field['placements'],['day','month','year'])]
        elif field['type']=='choice' and field.get('marks'):
            placement=field['marks'][value]
            rect=pymupdf.Rect(placement['bbox'])
            page=pdf[placement['page']-1]
            page.draw_line((rect.x0+1,rect.y0+1),(rect.x1-1,rect.y1-1),width=1)
            page.draw_line((rect.x0+1,rect.y1-1),(rect.x1-1,rect.y0+1),width=1)
            continue
        else:
            pieces=[value]*len(field['placements']) if field.get('repeat') else [value]
        if field.get('multiline'):
            lines=['']
            maxwidth=min(p['bbox'][2]-p['bbox'][0] for p in field['placements'])-2
            for word in value.split():
                candidate=(lines[-1]+' '+word).strip()
                if font.text_length(candidate,fontsize=9)>maxwidth:
                    lines.append(word)
                else:
                    lines[-1]=candidate
            if len(lines)>len(field['placements']):
                raise ValueError(field['label']+': text does not fit the official space')
            pieces=lines
        rendered=[]
        for placement,piece in zip(field['placements'],pieces):
            if placement.get('boxes'):
                if len(piece)>len(placement['boxes']):
                    raise ValueError(field['label']+': text exceeds the printed character boxes')
                rendered.extend((dict(page=placement['page'],bbox=box),character)
                    for box,character in zip(placement['boxes'],piece))
            else: rendered.append((placement,piece))
        for placement,piece in rendered:
            rect=pymupdf.Rect(placement['bbox'])
            size=10
            while size>7.5 and font.text_length(piece,fontsize=size)>rect.width-2:
                size-=0.25
            if font.text_length(piece,fontsize=size)>rect.width-2 or any(not font.has_glyph(ord(c)) for c in piece):
                raise ValueError(field['label']+': text does not fit or contains unsupported characters')
            page=pdf[placement['page']-1]
            # Cover the writable dots only, preserving every printed label.
            page.draw_rect(rect,color=None,fill=(1,1,1),overlay=True)
            baseline=rect.y0+(rect.height-size)/2+size*0.82
            page.insert_text((rect.x0+1,baseline),piece,fontname='FormFont',fontsize=size,color=(0,0,0),overlay=True)
    if draft:
        for page in pdf:
            page.insert_text((25,18),'TEMPLATE REVIEW DRAFT - FICTIONAL DATA ONLY',fontsize=8,color=(0.7,0,0))
    result=pdf.tobytes(garbage=4,deflate=True)
    pdf.close()
    return result


def token(values,mapping):
    digest=template_digest(mapping)
    body=json.dumps(dict(values=validate(values,mapping),template=digest,expires=int(time.time())+900),sort_keys=True,separators=(',',':')).encode()
    encoded=base64.urlsafe_b64encode(body).decode()
    return encoded+'.'+hmac.new(SECRET,encoded.encode(),hashlib.sha256).hexdigest()


def page_previews(payload):
    """Render the exact PDF in memory for browsers without a native PDF viewer."""
    with pymupdf.open(stream=payload,filetype='pdf') as pdf:
        return [dict(page_number=i+1,image_data_url='data:image/png;base64,'+
                     base64.b64encode(page.get_pixmap(matrix=pymupdf.Matrix(1.4,1.4),alpha=False).tobytes('png')).decode())
                for i,page in enumerate(pdf)]


def verify_token(values,value,mapping):
    try:
        encoded,signature=value.rsplit('.',1)
        if not hmac.compare_digest(hmac.new(SECRET,encoded.encode(),hashlib.sha256).hexdigest(),signature):
            raise ValueError()
        body=json.loads(base64.urlsafe_b64decode(encoded))
        if body['expires']<time.time() or body['values']!=validate(values,mapping) or body['template']!=template_digest(mapping):
            raise ValueError()
    except (ValueError,KeyError,TypeError):
        raise ValueError('Preview these exact values again before downloading') from None
