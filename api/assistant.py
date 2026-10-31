"""Grounded assistant; retrieval is replaceable through get_retriever()."""
import json
import os
import re
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from sqlalchemy.exc import SQLAlchemyError

from api.assistant_policy import PROMPT
from api.rag import ConversationStateError
from api.config import engine
from sqlalchemy import text
from api.assistant_documents import DocumentCard, document_cards, wants_documents, is_vietnamese, procedure_name, citation_title

router = APIRouter(prefix="/assistant", tags=["assistant"])


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Turn(Strict):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=16000)


class ChatRequest(Strict):
    message: str = Field(min_length=2, max_length=1000)
    procedure_code: str | None = Field(default=None, pattern=r"^\d\.\d{6}$")
    history: list[Turn] = Field(default_factory=list, max_length=12)
    retrieval_state: str | None = Field(default=None, max_length=12000)
    clarification_answer: str | None = Field(default=None, max_length=1000)


class Choice(Strict):
    id: str
    label: str


class Source(Strict):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    title: str = Field(min_length=1, max_length=500)
    url: HttpUrl
    text: str = Field(min_length=1, max_length=120000)
    evidence_status: dict = Field(default_factory=dict)


class Retrieval(Strict):
    sources: list[Source] = Field(default_factory=list, max_length=20)
    # Optional generated RAG answer is a routing/synthesis aid, not primary evidence.
    answer: str | None = Field(default=None, max_length=12000)
    clarification: str | None = Field(default=None, max_length=2000)
    choices: list[Choice] = Field(default_factory=list, max_length=20)
    retrieval_state: str | None = None
    procedure_code: str | None = None
    resolved_question: str | None = Field(default=None,max_length=1000)
    profile: dict = Field(default_factory=dict)
    documents: list[DocumentCard] = Field(default_factory=list)
    candidates: list[dict] = Field(default_factory=list, max_length=20)
    original_question: str | None = None
    context_notice: str | None = None

    @field_validator("sources")
    @classmethod
    def unique_ids(cls, sources):
        if len({s.id for s in sources}) != len(sources):
            raise ValueError("Source IDs must be unique")
        return sources


class DocumentPresentation(Strict):
    id: str
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(max_length=2000)
    condition: str | None = Field(max_length=1500)


class Generated(Strict):
    status: Literal["answered", "insufficient_context", "needs_clarification", "out_of_scope"]
    answer: str = Field(min_length=1, max_length=16000)
    source_ids: list[str] = Field(max_length=20)
    answer_basis: Literal['sources', 'general_guidance', 'mixed'] = 'sources'
    document_presentations: list[DocumentPresentation] = Field(default_factory=list)
    choice_labels: list[Choice] = Field(default_factory=list)


class Paragraph(Strict):
    text: str = Field(min_length=1, max_length=16000)
    source_ids: list[str] = Field(max_length=20)
    kind: Literal['procedure_fact', 'general_guidance'] = 'procedure_fact'


class Draft(Strict):
    status: Literal['answered', 'insufficient_context', 'needs_clarification', 'out_of_scope']
    paragraphs: list[Paragraph] = Field(min_length=1, max_length=20)
    document_presentations: list[DocumentPresentation] = Field(default_factory=list)
    choice_labels: list[Choice] = Field(default_factory=list)


class Citation(Strict):
    id: str
    title: str
    url: HttpUrl


class ChatResponse(Strict):
    status: Literal["answered", "insufficient_context", "needs_clarification", "out_of_scope"]
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    model: str | None = None
    choices: list[Choice] = Field(default_factory=list)
    retrieval_state: str | None = None
    procedure_code: str | None = None
    documents: list[DocumentCard] = Field(default_factory=list)
    answer_basis: Literal['sources', 'general_guidance', 'mixed'] = 'sources'


def retrieve(request: ChatRequest) -> Retrieval:
    from api.rag import retrieve as rag_retrieve
    return Retrieval.model_validate(rag_retrieve(request))


def get_retriever():
    return retrieve


@router.get('/setup')
def assistant_setup():
    base=os.getenv('ASSISTANT_BASE_URL','https://api.openai.com/v1').rstrip('/')
    configured=bool(os.getenv('ASSISTANT_MODEL') and (os.getenv('ASSISTANT_API_KEY') or
        (base=='https://api.openai.com/v1' and os.getenv('OPENAI_API_KEY'))))
    try:
        with engine().connect() as db:
            catalog=[dict(r) for r in db.execute(text('''SELECT p.code,s.name,m.profile->'aliases' AS aliases FROM procedure p
                JOIN source_page s ON s.id=p.current_snapshot_id
                LEFT JOIN rag_head h ON h.singleton
                LEFT JOIN rag_member m ON m.release_id=h.release_id AND m.code=p.code AND m.snapshot_id=s.id
                WHERE p.active ORDER BY p.code''')).mappings()]
            indexed=db.execute(text('SELECT EXISTS(SELECT 1 FROM rag_head)')).scalar_one()
    except SQLAlchemyError:
        raise HTTPException(503,'Database unavailable') from None
    # Generated routing aliases are display labels only, never factual evidence.
    catalog=[dict(code=p['code'],name=p['name'],name_en=next(
        (alias['text'] for alias in p.get('aliases') or [] if alias.get('language')=='en' and alias.get('text')),
        procedure_name(p['code']))) for p in catalog]
    return dict(generation_configured=configured,index_ready=indexed,procedures=catalog,
                model=os.getenv('ASSISTANT_MODEL'),reasoning_effort=os.getenv('ASSISTANT_REASONING_EFFORT') or None)


def build_messages(request: ChatRequest, evidence: Retrieval):
    # History is NOT promoted to trusted assistant turns. Even URLs/titles stay
    # in the data envelope; no client input is interpolated into system policy.
    payload = json.dumps({
        "question": evidence.resolved_question or request.message, "selected_procedure": evidence.procedure_code or request.procedure_code,
        "untrusted_history": [t.model_dump() for t in request.history],
        "retrieval": {"sources": [s.model_dump(mode="json") for s in evidence.sources],
                      "rag_draft": evidence.answer,"context_notice":evidence.context_notice},
        "pending_selection": {"question": evidence.clarification,
            "choices": [c.model_dump() for c in evidence.choices],
            "candidates": [{k:v for k,v in c.items() if k!='profile'} for c in evidence.candidates], "original_goal": evidence.original_question},
        "response_language": 'Vietnamese' if is_vietnamese(request.message) else 'Use the language of the user question, default English',
        "document_checklist": [{**d.model_dump(exclude={'form'}),"source_context":d._source_context} for d in evidence.documents],
        "document_panel": {"available":any(d.form for d in evidence.documents),
            "forms":[dict(card_id=d.id,document_id=d.form.document_id,form_id=d.form.form_id,
                title=d.title,requirement=d.requirement,condition=d.condition,
                review_status=d.form.review_status,applicability=d.form.applicability,
                download_available=d.form.download_available) for d in evidence.documents if d.form],
            "workflow":["Open the document card in the side panel", "View the blank document",
                "Choose Fill in fields", "Check fields", "Preview filled form",
                "Review the preview and download only when download_available is true"],
            "note":"Server-owned cards open a template and field panel. Draft templates use fictional data; final download stays locked until human review."},
    }, ensure_ascii=False)
    if len(payload) > 140000:
        raise HTTPException(413, "Assistant context is too large; narrow the retrieval")
    return [{"role": "system", "content": PROMPT}, {"role": "user", "content": payload}]


def output_format(evidence: Retrieval):
    # A small portable strict schema; runtime Pydantic limits still apply.
    result = {"type": "json_schema", "json_schema": {
        "name": "procedure_answer", "strict": True,
        "schema": {"type": "object", "additionalProperties": False,
            "required": ["status", "paragraphs"],
            "properties": {
                "status": {"type": "string", "enum": ["answered", "insufficient_context",
                                                       "needs_clarification", "out_of_scope"]},
                "paragraphs": {"type":"array", "minItems":1, "maxItems":20,
                    "items":{"type":"object", "additionalProperties":False,
                        "required":["text","source_ids","kind"], "properties":{
                            "text":{"type":"string", "description":"Plain text without citation markers, links or HTML. The server adds citations."},
                            "kind":{"type":"string", "enum":["procedure_fact","general_guidance"]},
                            "source_ids":{"type":"array", **({'maxItems':0} if not evidence.sources else {}),
                                "items":{"type":"string", **({'enum':[s.id for s in evidence.sources]} if evidence.sources else {})}}}}},
            }}}}
    if evidence.documents:
        schema=result['json_schema']['schema']
        schema['required'].append('document_presentations')
        schema['properties']['document_presentations']={"type":"array","minItems":len(evidence.documents),
            "maxItems":len(evidence.documents),"items":{"type":"object","additionalProperties":False,
            "required":["id","title","description","condition"],"properties":{
                "id":{"type":"string","enum":[d.id for d in evidence.documents]},
                "title":{"type":"string"},"description":{"type":"string"},
                "condition":{"type":["string","null"]}}}}
    if evidence.choices:
        schema=result['json_schema']['schema']
        schema['required'].append('choice_labels')
        schema['properties']['choice_labels']={"type":"array","minItems":len(evidence.choices),
            "maxItems":len(evidence.choices),"items":{"type":"object","additionalProperties":False,
            "required":["id","label"],"properties":{
                "id":{"type":"string","enum":[c.id for c in evidence.choices]},"label":{"type":"string"}}}}
    return result


def render_draft(draft: Draft, evidence: Retrieval) -> Generated:
    known = {s.id for s in evidence.sources}
    ids, paragraphs = [], []
    for paragraph in draft.paragraphs:
        if '[' in paragraph.text or ']' in paragraph.text:
            raise ValueError('Citations must use source_ids')
        cited = list(dict.fromkeys(paragraph.source_ids))
        if not set(cited) <= known:
            raise ValueError('Unknown citation')
        if paragraph.kind == 'procedure_fact' and not cited:
            raise ValueError('Procedural fact missing citations')
        paragraphs.append(paragraph.text + ''.join(' [' + sid + ']' for sid in cited))
        ids.extend(sid for sid in cited if sid not in ids)
    basis = 'mixed' if ids and any(p.kind=='general_guidance' and not p.source_ids for p in draft.paragraphs) else 'sources' if ids else 'general_guidance'
    if evidence.documents:
        expected={d.id for d in evidence.documents}
        if len(draft.document_presentations)!=len(expected) or {d.id for d in draft.document_presentations}!=expected:
            raise ValueError('Document translations must cover exactly the supplied cards')
        for presentation in draft.document_presentations:
            card=next(d for d in evidence.documents if d.id==presentation.id)
            if (card.condition is None)!=(presentation.condition is None):
                raise ValueError('Document condition cannot be removed or invented')
            if re.search(r'https?://|www\.|<[^>]+>|\[|\]',presentation.title+' '+presentation.description+' '+(presentation.condition or ''),re.I):
                raise ValueError('Unexpected document link or markup')
    elif draft.document_presentations:
        raise ValueError('Unexpected document cards')
    if len(draft.choice_labels)!=len(evidence.choices) or {c.id for c in draft.choice_labels}!={c.id for c in evidence.choices}:
        raise ValueError('Choice labels must preserve all server-owned IDs')
    if any(not c.label or len(c.label)>300 or re.search(r'https?://|<[^>]+>|\[|\]',c.label,re.I) for c in draft.choice_labels):
        raise ValueError('Invalid choice label')
    result = Generated(status=draft.status, answer='\n\n'.join(paragraphs), source_ids=ids, answer_basis=basis,
        document_presentations=draft.document_presentations,choice_labels=draft.choice_labels)
    validate_answer(result, evidence)
    return result


def validate_answer(result: Generated, evidence: Retrieval):
    known = {s.id for s in evidence.sources}
    cited = set(result.source_ids)
    # All brackets are reserved for citations by the response contract.
    markers = re.findall(r"\[([^\[\]\n]+)\]", result.answer)
    if len(cited) != len(result.source_ids) or not cited <= known or set(markers) != cited:
        raise ValueError("Invalid citation references")
    if result.status == "answered" and not cited and result.answer_basis != 'general_guidance':
        raise ValueError("Answer missing citations")
    if result.status == "out_of_scope" and cited:
        raise ValueError("Out of scope response must not cite evidence")
    # This rejects common active-content/link channels, not arbitrary semantic
    # injection. Callers must still render text, never HTML or auto-linked prose.
    if re.search(r"https?://|www\.|javascript:|data:|<[^>]+>|```|\]\s*\(", result.answer, re.I):
        raise ValueError("Unexpected link or active content")


def generate(request: ChatRequest, evidence: Retrieval) -> tuple[Generated, str]:
    model = os.getenv("ASSISTANT_MODEL", "").strip()
    base = os.getenv("ASSISTANT_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    # Never send the OpenAI credential to a custom provider by accident.
    key = os.getenv("ASSISTANT_API_KEY")
    if not key and base == "https://api.openai.com/v1":
        key = os.getenv("OPENAI_API_KEY")
    if not model or not key:
        raise HTTPException(503, "Configure ASSISTANT_MODEL and ASSISTANT_API_KEY")
    messages = build_messages(request, evidence)
    effort=os.getenv('ASSISTANT_REASONING_EFFORT','').strip()
    if effort and effort not in ('low','medium','high','xhigh','max'):
        raise HTTPException(503,'Invalid ASSISTANT_REASONING_EFFORT')
    options={"model":model,"messages":messages,"max_completion_tokens":8000,
             "response_format":output_format(evidence),"store":False}
    if effort:options['reasoning_effort']=effort
    try:
        response = httpx.post(base + "/chat/completions",
            headers={"Authorization": "Bearer " + key}, timeout=120,json=options)
        response.raise_for_status()
        choice = response.json()["choices"][0]
        if choice["finish_reason"] != "stop" or choice["message"].get("refusal") or choice["message"].get("tool_calls"):
            raise ValueError("Incomplete model response")
        result = render_draft(Draft.model_validate_json(choice["message"]["content"]), evidence)
        return result, model
    except httpx.TimeoutException:
        raise HTTPException(504, "Assistant provider timed out") from None
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
        raise HTTPException(502, "Assistant provider returned an unusable response") from None


def candidate_documents(evidence,query):
    """Offer scoped draft forms while keeping the office/procedure unresolved."""
    from api.assistant_context import present_evidence
    cards=[]
    for candidate in evidence.candidates:
        sources=[s for s in evidence.sources if s.id in candidate.get('source_ids',[])]
        if not sources or not candidate.get('evidence_available'): continue
        scoped=present_evidence(Retrieval(procedure_code=candidate['code'],sources=sources,profile=candidate.get('profile',{})))
        aliases=scoped.sources[0].evidence_status['source_id_map']
        for card in document_cards(scoped,query):
            if not card.form: continue
            card.source_ids=[aliases[sid] for sid in card.source_ids]
            card.requirement='unconfirmed'
            card.condition='This draft belongs to the '+procedure_name(candidate['code'])+' option. Your receiving office has not been selected.'
            card._source_context['selection_notice']=card.condition
            cards.append(card)
    return cards


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, retriever=Depends(get_retriever)):
    try:
        evidence = Retrieval.model_validate(retriever(request))
    except ConversationStateError as exc:
        raise HTTPException(409,str(exc)) from None
    except LookupError:
        raise HTTPException(404, "Procedure context not found") from None
    except RuntimeError:
        raise HTTPException(409, "Retrieval is not ready or context is not validated") from None
    except (SQLAlchemyError, httpx.HTTPError, ValueError, TypeError):
        raise HTTPException(503, "Retrieval unavailable") from None
    if evidence.clarification or not evidence.sources:
        evidence=evidence.model_copy(update={'documents':candidate_documents(evidence,request.message)})
        # A pending choice is conversation context, not a canned response. The
        # model may explain/compare, but cannot select or unlock a procedure.
        result, model = generate(request, evidence)
        presentations={d.id:d for d in result.document_presentations}
        documents=[d.model_copy(update=presentations[d.id].model_dump(exclude={'id'})) if d.id in presentations else d for d in evidence.documents]
        if result.status=='out_of_scope': documents=[]
        cited=set(result.source_ids) | {sid for d in documents for sid in d.source_ids}
        citations=[Citation(id=s.id,title=citation_title(s,None,request.message),url=s.url)
                   for s in evidence.sources if s.id in cited]
        return ChatResponse(status=result.status,answer=result.answer,citations=citations,model=model,
            choices=result.choice_labels or evidence.choices,retrieval_state=evidence.retrieval_state,
            procedure_code=evidence.procedure_code,
            documents=documents,
            answer_basis=result.answer_basis)
    from api.assistant_context import present_evidence
    complete = present_evidence(evidence)
    query = evidence.resolved_question or request.message
    available = document_cards(complete, query)
    documents = available if wants_documents(query) else [d for d in available if d.form]
    # Supply the complete captured procedure. Keyword-based section pruning can
    # hide exceptions or make the model claim an omitted requirement is absent.
    evidence = complete.model_copy(update={'documents':documents})
    result, model = generate(request, evidence)
    presentations={d.id:d for d in result.document_presentations}
    documents=[d.model_copy(update=presentations[d.id].model_dump(exclude={'id'})) if d.id in presentations else d for d in documents]
    # Cards refer to complete evidence IDs. Restore those sources for citations.
    evidence = complete
    # A sponsor follow-up must not hide verified documents for a selected procedure.
    if result.status == 'out_of_scope':
        documents = []
    cited = set(result.source_ids) | {sid for doc in documents for sid in doc.source_ids}
    citations = [Citation(id=s.id, title=citation_title(s,evidence.procedure_code,request.message), url=s.url)
                 for s in evidence.sources if s.id in cited]
    return ChatResponse(status=result.status, answer=result.answer, citations=citations, model=model,
                        procedure_code=evidence.procedure_code,retrieval_state=evidence.retrieval_state,documents=documents,
                        answer_basis=result.answer_basis)
