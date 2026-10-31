"""Cited checklist cards and server-owned form actions. No applicant data or LLM URLs."""
import hashlib
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from api.rag import normalize


class FormAction(BaseModel):
    model_config = ConfigDict(extra='forbid')
    form_id: str
    document_id: str
    procedure_code: str
    template_sha256: str
    template_version: str
    revision: str
    review_status: str
    applicability: str = 'unresolved'
    download_available: bool
    schema_url: str
    template_url: str
    template_pages_url: str
    validate_url: str
    preview_url: str
    preview_pages_url: str
    download_url: str


class DocumentCard(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str
    title: str
    kind: Literal['fillable_form', 'supporting_document', 'submission_instruction']
    requirement: Literal['required', 'conditional', 'unconfirmed']
    condition: str | None = None
    description: str = ''
    originals: int | None = None
    copies: int | None = None
    source_ids: list[str] = Field(default_factory=list)
    evidence_status: str
    form: FormAction | None = None


def is_vietnamese(query):
    text = normalize(query)
    if re.search(r'\b(in english|answer in english)\b', text):
        return False
    return bool(re.search(r'\b(toi|muon|giay to|ho so|thu tuc|gia han|tam tru|bao lau|le phi|tieng viet|in vietnamese|phien ban|dien mau|co quan|cap tinh|trung uong|chua ro)\b', text))


def procedure_name(code):
    return {'1.001146':'Stay extension — provincial immigration office',
            '1.003326':'Stay extension — central Immigration Department',
            '1.000771':'Stay extension using a visa exemption certificate',
            '1.003342':'Visa issuance — central Immigration Department'}.get(code,'Procedure '+code)


def citation_title(source, code, query):
    if is_vietnamese(query) or '| ' not in source.title:
        return source.title.split(' | ')[0] if is_vietnamese(query) else source.title
    role=source.title.split(' | ')[1]
    label={'primary':'Official procedure page','supplementary':'Additional official guidance'}.get(role,'Official form')
    return label+' — '+procedure_name(code or '')


def wants_documents(query):
    text=normalize(query)
    if re.search(r'\b(document|documents|checklist|paperwork|form|prepare|ho so|giay to|mau|chuan bi)\b',text):return True
    from api.form_registry import entries
    return any(re.search(r'(?<!\w)'+re.escape(normalize(row['form_id']))+r'(?!\w)',text) for row in entries())


def form_action(code,form_id):
    from api.form_registry import for_form
    installed=for_form(code,form_id)
    return FormAction(**installed.action()) if installed else None


def document_cards(evidence, query):
    """Use only the selected release's profile and quote-checked source references."""
    vi = is_vietnamese(query)
    from api.form_registry import entries
    form_ids={row['form_id'] for row in entries()}
    form_ids.update(r['form_code']['value'] for r in evidence.profile.get('form_relationships',[])
                    if r.get('form_code',{}).get('status')=='supported' and r['form_code'].get('value'))
    def say(en, vn): return vn if vi else en
    role_map = {}
    for source in evidence.sources:
        for role in ('primary', 'supplementary'):
            if '| ' + role + ' |' in source.title:
                role_map[role] = source

    def refs(fact):
        found = []
        for ref in fact.get('source_refs', []):
            source = role_map.get(ref.get('source_id'))
            quote = ref.get('quote') or ''
            if source and quote and ' '.join(quote.split()) in ' '.join(source.text.split()):
                found.append((source.id, quote))
        return found

    cards = []
    for row in evidence.profile.get('required_documents', []):
        name_fact = row.get('name', {})
        citations = refs(name_fact)
        if not citations or name_fact.get('status') not in ('supported', 'conflict'):
            continue
        name = name_fact.get('value') or ''
        normalized = normalize(name)
        matched_form=next((form_id for form_id in sorted(form_ids)
            if re.search(r'(?<!\w)'+re.escape(normalize(form_id))+r'(?!\w)',normalized)
            and all(re.search(r'(?<!\w)'+re.escape(normalize(form_id))+r'(?!\w)',normalize(q)) for _,q in citations)),None)
        condition_fact = row.get('required_when', {})
        condition_refs = refs(condition_fact)
        condition = say('Confirm whether this applies to your situation.', 'Cần xác nhận mục này có áp dụng cho trường hợp của bạn không.')
        requirement = 'unconfirmed'
        if condition_refs and condition_fact.get('operator') == 'true':
            requirement, condition = 'required', None
        elif condition_refs and condition_fact.get('operator') == 'eq':
            key, values = condition_fact.get('criterion_key'), condition_fact.get('values', [])
            if key == 'sponsor_type' and values in (['vietnamese_citizen'], ['vietnamese_citizen_relative']):
                requirement = 'conditional'
                condition = say('If a Vietnamese citizen sponsors their relative.', 'Khi công dân Việt Nam bảo lãnh cho thân nhân.')
            elif key == 'visa_format' and values == ['separate']:
                requirement = 'conditional'
                condition = say('Only for a separate-sheet visa; not a general stay-extension requirement.', 'Chỉ khi cấp thị thực rời; không phải yêu cầu chung của thủ tục gia hạn tạm trú.')
        citations += condition_refs
        kind, action = 'supporting_document', None
        description = ''
        if 'bo ho so' in normalized and 'khong phai giay to' in normalized:
            title, kind = say('One complete set', 'Một bộ hồ sơ'), 'submission_instruction'
            description = say('Submit one complete set of the required documents.', 'Nộp một bộ đầy đủ các giấy tờ cần thiết.')
        elif 'huong dan' in normalized:
            kind, requirement = 'submission_instruction', 'conditional'
            title = say('Online filing', 'Nộp hồ sơ trực tuyến')
            condition = say('If you apply online.', 'Nếu nộp trực tuyến.')
            # This translation is used only for the known, fully quoted instruction.
            quotes = normalize(' '.join(q for _, q in refs(name_fact)))
            if all(s in quotes for s in ('ho chieu', 'buu chinh', 'chung thuc dien tu', 'chua')):
                description = say('Send the passport or travel document to the receiving office by public postal service. Other documents need electronic certification; otherwise send them by public post.',
                    'Gửi hộ chiếu hoặc giấy tờ đi lại quốc tế qua bưu chính công ích đến cơ quan tiếp nhận. Các giấy tờ khác cần chứng thực điện tử; nếu chưa có, gửi qua bưu chính công ích.')
            else:
                description, requirement = say('This instruction needs further review. Check the cited source with the receiving office.',name), 'unconfirmed'
        elif matched_form:
            title, kind = say('Form '+matched_form, 'Tờ khai '+matched_form), 'fillable_form'
            action = form_action(evidence.procedure_code,matched_form)
            description = say('Complete the application form.', 'Điền tờ khai.')
            if name_fact['status']=='conflict':
                description += say(' Confirm the accepted edition with the receiving office; the captured sources cite different versions.',
                    ' Cần xác nhận phiên bản được cơ quan tiếp nhận chấp nhận vì các nguồn đang ghi khác phiên bản.')
            elif action and action.applicability=='unresolved':
                description += say(' Confirm the accepted edition with the receiving office.', ' Xác nhận phiên bản được cơ quan tiếp nhận chấp nhận.')
        elif 'ho chieu' in normalized:
            title = say('Passport or international travel document', 'Hộ chiếu hoặc giấy tờ đi lại quốc tế')
            if 'thuong tru' in normalized:
                description = say('For overseas Vietnamese, the source also lists a foreign-issued permanent-residence document as an alternative.',
                    'Đối với người Việt Nam định cư ở nước ngoài, nguồn còn nêu giấy tờ cho phép thường trú do cơ quan nước ngoài cấp.')
        elif 'giay mien thi thuc' in normalized:
            title = say('Visa exemption certificate', 'Giấy miễn thị thực')
        elif 'chung minh quan he' in normalized:
            title = say('Proof of family relationship', 'Giấy tờ chứng minh quan hệ gia đình')
        elif re.search(r'\banh\b', normalized):
            title = say('Photographs', 'Ảnh')
            description = say('Check the applicable branch and photo count with the receiving office. You do not need to upload a photo here.',
                'Xác nhận trường hợp áp dụng và số lượng ảnh với cơ quan tiếp nhận. Bạn không cần tải ảnh lên đây.')
        else:
            title, requirement = say('Additional requirement — needs confirmation',name), 'unconfirmed'
            description=say('This extracted item needs clarification before it can be presented as a requirement. Check the cited source with the receiving office.', '')
        counts = {}
        for key in ('originals', 'copies'):
            fact = row.get(key, {})
            verified = refs(fact)
            if kind != 'submission_instruction' and fact.get('status') == 'supported' and verified and re.fullmatch(r'\d+', str(fact.get('value'))):
                counts[key] = int(fact['value'])
                citations += verified
        cards.append(DocumentCard(id=hashlib.sha256(((evidence.procedure_code or '')+name).encode()).hexdigest()[:16],
            title=title, kind=kind, requirement=requirement, condition=condition, description=description,
            source_ids=list(dict.fromkeys(sid for sid, _ in citations)), evidence_status=name_fact['status'], form=action, **counts))
    return cards
