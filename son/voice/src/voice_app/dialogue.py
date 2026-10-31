"""Vietnamese/English intent routing. No generated or translated legal facts."""
from dataclasses import dataclass
import re
import unicodedata

from .languages import Language, MESSAGES, choices, response


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


CHOICES = choices("vi")
WELCOME = MESSAGES["vi"]["welcome"]


def advance(previous: DialogueState, utterance: str, language: Language = "vi") -> tuple[DialogueState, dict]:
    def result(state, key, code=None, with_choices=False, **values):
        return response(language, state, key, code, with_choices, **values)

    def has(*phrases):
        return any(contains(value, phrase) for phrase in phrases)

    value = normalize(utterance)
    if not value:
        return previous, result("clarify", "repeat", with_choices=True)
    if has("ho so cua toi", "du lieu ca nhan", "thong tin ca nhan", "so dien thoai cua toi", "cccd cua toi", "dossier", "my dossier", "my personal", "read my phone number", "my profile", "read my passport", "access my passport", "my records"):
        return previous, result("personal_access_unavailable", "personal")
    if has("lam lai", "bat dau lai", "doi thu tuc", "start over", "restart", "change procedure"):
        return DialogueState(awaiting_choice=True), result("clarify", "clarify", with_choices=True)
    if has("thuong tru", "ho chieu", "passport", "can cuoc", "visa", "nguoi nuoc ngoai", "ket hon", "khai sinh", "kinh doanh", "permanent residence", "identity card", "foreigner", "foreign national", "foreign citizen", "temporary residence card", "trc", "marriage", "birth certificate", "business"):
        return DialogueState(), result("not_covered", "unsupported")
    residence = has("tam tru", "temporary residence", "temporary residency")
    renewal = has("gia han", "renew", "renewal", "extend", "extension")
    # Past registration is context, not a second requested action.
    registration_text = value.replace("da dang ky", "").replace("tung dang ky", "").replace("gia han dang ky", "gia han")
    registration_text = registration_text.replace("renew registration", "renew").replace("extend registration", "extend")
    registration = any(contains(registration_text, phrase) for phrase in ("dang ky", "register", "first time", "lan dau"))
    registration = registration or (contains(registration_text, "registration") and (not renewal or has("and", "or")))
    relevant = residence or previous.awaiting_choice
    # Negation and mixed actions require clarification rather than a nearest hit.
    if relevant and (has("khong", "not", "don t", "dont", "do not") or (renewal and registration)):
        return DialogueState(awaiting_choice=True), result("clarify", "clarify", with_choices=True)
    if relevant and (renewal or registration):
        code = "1.002755" if renewal else "1.004194"
        name = MESSAGES[language]["renew" if renewal else "register"]
        return DialogueState(candidate_code=code), result("lookup_pending", "pending", code, name=name)
    if residence:
        return DialogueState(awaiting_choice=True), result("clarify", "clarify", with_choices=True)
    if previous.candidate_code and has("giay to", "le phi", "ho so", "can gi", "bao nhieu", "documents", "fees", "checklist", "how much", "what do i need"):
        return previous, result("lookup_pending", "facts_pending", previous.candidate_code)
    return DialogueState(), result("not_found", "not_found", with_choices=True)
