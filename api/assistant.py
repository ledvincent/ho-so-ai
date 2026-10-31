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

    @field_validator("sources")
    @classmethod
    def unique_ids(cls, sources):
        if len({s.id for s in sources}) != len(sources):
            raise ValueError("Source IDs must be unique")
        return sources


class Generated(Strict):
    status: Literal["answered", "insufficient_context", "needs_clarification", "out_of_scope"]
    answer: str = Field(min_length=1, max_length=16000)
    source_ids: list[str] = Field(max_length=20)


class Paragraph(Strict):
    text: str = Field(min_length=1, max_length=16000)
    source_ids: list[str] = Field(max_length=20)


class Draft(Strict):
    status: Literal['answered', 'insufficient_context', 'needs_clarification', 'out_of_scope']
    paragraphs: list[Paragraph] = Field(min_length=1, max_length=20)


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


def retrieve(request: ChatRequest) -> Retrieval:
    from api.rag import retrieve as rag_retrieve
    result=Retrieval.model_validate(rag_retrieve(request))
    if result.clarification:
        vi=is_vietnamese(request.message)
        translations={'What do you want to do?':'Tôi có thể giúp bạn xác định thủ tục và chuẩn bị giấy tờ. Gia hạn tạm trú và xin cấp thị thực là hai việc khác nhau, dù có thể dùng cùng mẫu đơn. Bạn muốn tiếp tục thời gian lưu trú hiện tại hay xin cấp thị thực?',
            'Which processing level do you need?':'Có thủ tục gia hạn tại cơ quan cấp tỉnh và tại Cục Quản lý xuất nhập cảnh. Cơ quan tiếp nhận hoặc người bảo lãnh đã hướng dẫn bạn nộp ở đâu chưa? Nếu chưa rõ, bạn có thể chọn “Tôi chưa rõ”.',
            'Which procedure do you mean?':'Có một vài thủ tục gần giống nhau. Bạn hãy chọn trường hợp phù hợp nhất bên dưới; không cần biết mã thủ tục. Nếu vẫn chưa rõ, hãy nói điều bạn đang muốn làm.',
            'Extend my stay':'Gia hạn tạm trú','Apply for a visa':'Đề nghị cấp thị thực',
            'Provincial immigration office':'Cơ quan quản lý xuất nhập cảnh cấp tỉnh',
            'Central immigration department':'Cục Quản lý xuất nhập cảnh',"I'm not sure":'Tôi chưa rõ'}
        english={'1.001146':'Extend a stay — provincial immigration office',
            '1.003326':'Extend a stay — central Immigration Department',
            '1.000771':'Extend a stay using a visa exemption certificate',
            '1.003342':'Apply for a visa — central Immigration Department'}
        introductions={'What do you want to do?':"I can help you work out the right procedure and prepare the paperwork. Extending your current stay and applying for a visa are different requests, even though they can use the same form. Which best describes what you want to do?",
            'Which processing level do you need?':"There are stay-extension procedures handled by provincial immigration offices and by the central Immigration Department. Has your sponsor or an immigration office told you where to apply? If you haven't been told, choose “I'm not sure”.",
            'Which procedure do you mean?':"A few related procedures match. Choose the situation that sounds closest; you don't need to know a procedure code. If none is clear, describe what you're trying to do."}
        result.clarification=(translations if vi else introductions).get(result.clarification,result.clarification)
        result.choices=[c.model_copy(update={'label':translations.get(c.label,c.label) if vi else english.get(c.id,c.label)}) for c in result.choices]
    return result


def get_retriever():
    return retrieve


@router.get('/setup')
def assistant_setup():
    base=os.getenv('ASSISTANT_BASE_URL','https://api.openai.com/v1').rstrip('/')
    configured=bool(os.getenv('ASSISTANT_MODEL') and (os.getenv('ASSISTANT_API_KEY') or
        (base=='https://api.openai.com/v1' and os.getenv('OPENAI_API_KEY'))))
    try:
        with engine().connect() as db:
            catalog=[dict(r) for r in db.execute(text('''SELECT p.code,s.name FROM procedure p
                JOIN source_page s ON s.id=p.current_snapshot_id WHERE p.active ORDER BY p.code''')).mappings()]
            indexed=db.execute(text('SELECT EXISTS(SELECT 1 FROM rag_head)')).scalar_one()
    except SQLAlchemyError:
        raise HTTPException(503,'Database unavailable') from None
    catalog=[{**p,'name_en':procedure_name(p['code'])} for p in catalog]
    return dict(generation_configured=configured,index_ready=indexed,procedures=catalog,
                model=os.getenv('ASSISTANT_MODEL'),reasoning_effort=os.getenv('ASSISTANT_REASONING_EFFORT') or None)


def build_messages(request: ChatRequest, evidence: Retrieval):
    # History is NOT promoted to trusted assistant turns. Even URLs/titles stay
    # in the data envelope; no client input is interpolated into system policy.
    payload = json.dumps({
        "question": evidence.resolved_question or request.message, "selected_procedure": evidence.procedure_code or request.procedure_code,
        "untrusted_history": [t.model_dump() for t in request.history],
        "retrieval": {"sources": [s.model_dump(mode="json") for s in evidence.sources],
                      "rag_draft": evidence.answer},
        "response_language": 'Vietnamese' if is_vietnamese(request.message) else 'Use the language of the user question, default English',
        "document_checklist": [d.model_dump(exclude={'form'}) for d in evidence.documents],
        "document_panel": {"available":any(d.form for d in evidence.documents),
            "note":"Server-owned cards open a template and field panel. Draft templates use fictional data; final download stays locked until human review."},
    }, ensure_ascii=False)
    if len(payload) > 140000:
        raise HTTPException(413, "Assistant context is too large; narrow the retrieval")
    return [{"role": "system", "content": PROMPT}, {"role": "user", "content": payload}]


def output_format(evidence: Retrieval):
    # A small portable strict schema; runtime Pydantic limits still apply.
    return {"type": "json_schema", "json_schema": {
        "name": "procedure_answer", "strict": True,
        "schema": {"type": "object", "additionalProperties": False,
            "required": ["status", "paragraphs"],
            "properties": {
                "status": {"type": "string", "enum": ["answered", "insufficient_context",
                                                       "needs_clarification", "out_of_scope"]},
                "paragraphs": {"type":"array", "minItems":1, "maxItems":20,
                    "items":{"type":"object", "additionalProperties":False,
                        "required":["text","source_ids"], "properties":{
                            "text":{"type":"string", "description":"Plain text without citation markers, links or HTML. The server adds citations."},
                            "source_ids":{"type":"array", "items":{"type":"string", "enum":[s.id for s in evidence.sources]}}}}},
            }}}}


def render_draft(draft: Draft, evidence: Retrieval) -> Generated:
    known = {s.id for s in evidence.sources}
    ids, paragraphs = [], []
    for paragraph in draft.paragraphs:
        if '[' in paragraph.text or ']' in paragraph.text:
            raise ValueError('Citations must use source_ids')
        cited = list(dict.fromkeys(paragraph.source_ids))
        if not set(cited) <= known:
            raise ValueError('Unknown citation')
        paragraphs.append(paragraph.text + ''.join(' [' + sid + ']' for sid in cited))
        ids.extend(sid for sid in cited if sid not in ids)
    result = Generated(status=draft.status, answer='\n\n'.join(paragraphs), source_ids=ids)
    validate_answer(result, evidence)
    return result


def validate_answer(result: Generated, evidence: Retrieval):
    known = {s.id for s in evidence.sources}
    cited = set(result.source_ids)
    # All brackets are reserved for citations by the response contract.
    markers = re.findall(r"\[([^\[\]\n]+)\]", result.answer)
    if len(cited) != len(result.source_ids) or not cited <= known or set(markers) != cited:
        raise ValueError("Invalid citation references")
    if result.status == "answered" and not cited:
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
    if evidence.clarification:
        return ChatResponse(status="needs_clarification", answer=evidence.clarification,
                            choices=evidence.choices,retrieval_state=evidence.retrieval_state)
    if not evidence.sources:
        return ChatResponse(status="insufficient_context",
                            answer=("Bạn hãy mô tả điều mình muốn làm bằng lời của bạn, chẳng hạn gia hạn thời gian lưu trú hoặc xin cấp thị thực. Tôi sẽ giúp xác định thủ tục phù hợp, giải thích giấy tờ cần chuẩn bị và hướng dẫn bước tiếp theo. Bạn đang muốn giải quyết việc gì?"
                                    if is_vietnamese(request.message) else "Tell me what you'd like to get done in your own words—for example, extending your stay or applying for a visa. I can help identify the relevant procedure, explain the paperwork, and guide you through the next steps. What are you trying to arrange?"))
    from api.assistant_context import present_evidence, focus_evidence
    complete = present_evidence(evidence)
    query = evidence.resolved_question or request.message
    documents = document_cards(complete, query) if wants_documents(query) else []
    evidence = focus_evidence(evidence, query).model_copy(update={'documents':documents})
    result, model = generate(request, evidence)
    # Cards refer to complete evidence IDs. Restore those sources for citations.
    evidence = complete
    # A sponsor follow-up must not hide verified documents for a selected procedure.
    if result.status == 'out_of_scope':
        documents = []
    cited = set(result.source_ids) | {sid for doc in documents for sid in doc.source_ids}
    citations = [Citation(id=s.id, title=citation_title(s,evidence.procedure_code,request.message), url=s.url)
                 for s in evidence.sources if s.id in cited]
    return ChatResponse(status=result.status, answer=result.answer, citations=citations, model=model,
                        procedure_code=evidence.procedure_code,retrieval_state=evidence.retrieval_state,documents=documents)
