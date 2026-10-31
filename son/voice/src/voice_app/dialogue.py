"""Conservative Vietnamese intent routing. No generated legal information."""
from dataclasses import dataclass
import re
import unicodedata


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFD", value.casefold().replace("đ", "d"))
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9\s]", " ", value).split())


def contains(value: str, phrase: str) -> bool:
    return f" {phrase} " in f" {value} "


@dataclass(frozen=True)
class DialogueState:
    awaiting_choice: bool = False
    candidate_code: str | None = None


CHOICES = [
    {"label": "Đăng ký tạm trú lần đầu", "text": "Tôi muốn đăng ký tạm trú"},
    {"label": "Gia hạn tạm trú", "text": "Tôi muốn gia hạn tạm trú"},
]

WELCOME = "Xin chào! Bạn muốn đăng ký tạm trú lần đầu hay gia hạn tạm trú? Chỉ mô tả nhu cầu, không đọc thông tin cá nhân."
CLARIFY = "Bạn muốn đăng ký tạm trú lần đầu hay gia hạn đăng ký tạm trú đã có?"
PENDING = "Tôi đã ghi nhận nhu cầu {name}. Dữ liệu thủ tục đã duyệt chưa được kết nối, nên tôi chưa thể đọc danh sách giấy tờ hoặc lệ phí."


def result(state: str, reply: str, candidate_code: str | None = None, choices: bool = False) -> dict:
    return {"state": state, "reply": reply, "candidate_code": candidate_code,
            "choices": CHOICES if choices else [], "reviewed_lookup_available": False}


def advance(previous: DialogueState, utterance: str) -> tuple[DialogueState, dict]:
    value = normalize(utterance)
    if not value:
        return previous, result("clarify", "Tôi chưa nghe rõ. Bạn có thể nói lại hoặc nhập nội dung?", choices=True)
    if any(contains(value, phrase) for phrase in ("ho so cua toi", "du lieu ca nhan", "thong tin ca nhan", "so dien thoai cua toi", "cccd cua toi", "dossier")):
        return previous, result("personal_access_unavailable", "Tôi chưa có quyền truy cập hồ sơ cá nhân. Kết nối đăng nhập và xác nhận quyền truy cập chưa sẵn sàng. Bạn có thể hỏi về nhu cầu tạm trú nói chung.")
    if any(contains(value, phrase) for phrase in ("lam lai", "bat dau lai", "doi thu tuc")):
        return DialogueState(awaiting_choice=True), result("clarify", CLARIFY, choices=True)
    if any(contains(value, phrase) for phrase in ("thuong tru", "ho chieu", "passport", "can cuoc", "visa", "nguoi nuoc ngoai", "ket hon", "khai sinh", "kinh doanh")):
        return DialogueState(), result("not_covered", "Bản thử nghiệm này chỉ hỗ trợ định hướng đăng ký hoặc gia hạn tạm trú cho công dân Việt Nam. Nhu cầu này chưa nằm trong phạm vi hỗ trợ.")
    residence = contains(value, "tam tru")
    renewal = contains(value, "gia han")
    # Past registration is context, not a second requested action.
    registration_text = value.replace("da dang ky", "").replace("tung dang ky", "").replace("gia han dang ky", "gia han")
    registration = contains(registration_text, "dang ky") or contains(value, "lan dau")
    relevant = residence or previous.awaiting_choice
    # Negation and mixed actions require clarification rather than a nearest hit.
    if relevant and (contains(value, "khong") or (renewal and registration)):
        return DialogueState(awaiting_choice=True), result("clarify", CLARIFY, choices=True)
    if relevant and (renewal or registration):
        code = "1.002755" if renewal else "1.004194"
        name = "gia hạn tạm trú" if renewal else "đăng ký tạm trú"
        return DialogueState(candidate_code=code), result("lookup_pending", PENDING.format(name=name), code)
    if residence:
        return DialogueState(awaiting_choice=True), result("clarify", CLARIFY, choices=True)
    if previous.candidate_code and any(contains(value, phrase) for phrase in ("giay to", "le phi", "ho so", "can gi", "bao nhieu")):
        return previous, result("lookup_pending", "Tôi chưa có dữ liệu thủ tục đã duyệt cho nhu cầu vừa chọn. Tôi sẽ không đoán giấy tờ, điều kiện hay lệ phí.", previous.candidate_code)
    return DialogueState(), result("not_found", "Tôi chưa xác định được nhu cầu tạm trú trong nội dung này. Bạn có thể chọn một trong hai nhu cầu sau.", choices=True)
