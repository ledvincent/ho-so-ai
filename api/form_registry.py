"""Installed document definitions. Each ID binds a procedure, template and field schema."""
import json
import re
from dataclasses import dataclass
from pathlib import Path
from api.config import ROOT
from api import form_engine

REGISTRY_PATH=ROOT/'data/forms/registry.json'


@dataclass(frozen=True)
class Document:
    entry: dict
    mapping: dict

    @property
    def id(self): return self.entry['document_id']

    def version(self): return form_engine.template_digest(self.mapping)

    def schema(self):
        import pymupdf
        version=self.version()
        with pymupdf.open(ROOT/self.mapping['pdf_path']) as pdf: pages=len(pdf)
        return dict(document_id=self.id,procedure_code=self.entry['procedure_code'],
            form_id=self.entry['form_id'],name=self.entry['name'],
            revision=self.mapping['revision_reference'],effective_from=self.mapping.get('effective_from'),
            review_status=self.mapping['review_status'],fields=self.mapping['fields'],
            fixed_values=self.mapping.get('fixed_values',{}),date_order=self.mapping.get('date_order',[]),
            template_version=version,template_sha256=self.mapping['form_sha256'],page_count=pages,
            download_available=self.mapping['review_status']=='reviewed',
            applicability=self.entry.get('applicability','unresolved'))

    def action(self):
        schema=self.schema()
        keys=('document_id','form_id','procedure_code','template_sha256','template_version','revision',
              'review_status','download_available','applicability')
        base='/documents/'+self.id
        result={key:schema[key] for key in keys}
        for key,path in [('schema','schema'),('template','template'),('template_pages','template-pages'),
                         ('validate','validate'),('preview','preview'),('preview_pages','preview-pages'),
                         ('download','download')]:result[key+'_url']=base+'/'+path
        return result


def entries():
    rows=json.loads(REGISTRY_PATH.read_text(encoding='utf-8'))
    ids=[row['document_id'] for row in rows]
    if len(ids)!=len(set(ids)) or any(not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,99}',i) for i in ids):
        raise ValueError('Invalid installed document registry')
    return rows


def local_file(relative,folder=ROOT):
    path=(ROOT/relative).resolve()
    if not path.is_relative_to(folder.resolve()) or not path.is_file():
        raise ValueError('Installed document file unavailable')
    return path


def get_document(document_id):
    entry=next((r for r in entries() if r['document_id']==document_id),None)
    if entry is None:raise LookupError('Document workflow is not installed')
    mapping=json.loads(local_file(entry['spec_path'],ROOT/'data/forms').read_text(encoding='utf-8'))
    if mapping['procedure_code']!=entry['procedure_code']:
        raise ValueError('Document procedure binding mismatch')
    local_file(mapping['pdf_path'],ROOT/'data/forms')
    # Identity is included in the version/token digest, preventing cross-document reuse.
    mapping={**mapping,'document_id':document_id,'form_id':entry['form_id']}
    return Document(entry,mapping)


def for_procedure(code):
    return [get_document(row['document_id']) for row in entries() if row['procedure_code']==code]


def for_form(code,form_id):
    found=[d for d in for_procedure(code) if d.entry['form_id'].casefold()==form_id.casefold()]
    return found[0] if len(found)==1 else None
