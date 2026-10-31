"""Canned dialogue messages, not translations of official procedure facts."""
from typing import Literal

Language = Literal["vi", "en"]
SPEECH_LANGUAGES = {"vi": "vi-VN", "en": "en-US"}

MESSAGES = {
    "vi": {
        "welcome": "Xin chào! Bạn muốn đăng ký tạm trú lần đầu hay gia hạn tạm trú? Chỉ mô tả nhu cầu, không đọc thông tin cá nhân.",
        "clarify": "Bạn muốn đăng ký tạm trú lần đầu hay gia hạn đăng ký tạm trú đã có?",
        "repeat": "Tôi chưa nghe rõ. Bạn có thể nói lại hoặc nhập nội dung?",
        "personal": "Tôi chưa có quyền truy cập hồ sơ cá nhân. Kết nối đăng nhập và xác nhận quyền truy cập chưa sẵn sàng. Bạn có thể hỏi về nhu cầu tạm trú nói chung.",
        "unsupported": "Bản thử nghiệm này chỉ hỗ trợ định hướng đăng ký hoặc gia hạn tạm trú cho công dân Việt Nam. Nhu cầu này chưa nằm trong phạm vi hỗ trợ.",
        "pending": "Tôi đã ghi nhận nhu cầu {name}. Dữ liệu thủ tục đã duyệt chưa được kết nối, nên tôi chưa thể đọc danh sách giấy tờ hoặc lệ phí.",
        "facts_pending": "Tôi chưa có dữ liệu thủ tục đã duyệt cho nhu cầu vừa chọn. Tôi sẽ không đoán giấy tờ, điều kiện hay lệ phí.",
        "not_found": "Tôi chưa xác định được nhu cầu tạm trú trong nội dung này. Bạn có thể chọn một trong hai nhu cầu sau.",
        "register": "đăng ký tạm trú", "renew": "gia hạn tạm trú",
    },
    "en": {
        "welcome": "Hello! Do you want to register temporary residence for the first time, or renew an existing registration? Describe your need without sharing personal information. This demo covers Vietnamese citizens only.",
        "clarify": "Do you want to register temporary residence for the first time, or renew an existing registration?",
        "repeat": "I did not catch that. Could you repeat it or type your request?",
        "personal": "I cannot access personal dossiers. Sign-in and access approval are not connected yet. You can describe your general temporary-residence need.",
        "unsupported": "This demo only routes temporary-residence registration or renewal for Vietnamese citizens. Your request is not covered.",
        "pending": "I understand that you want to {name}. Reviewed procedure data is not connected yet, so I cannot provide a document checklist or fees.",
        "facts_pending": "Reviewed data for your selected procedure is not available yet. I will not guess documents, conditions, or fees.",
        "not_found": "I could not identify a temporary-residence request. You can choose one of the following options.",
        "register": "register temporary residence", "renew": "renew temporary-residence registration",
    },
}


def choices(language: Language):
    if language == "en":
        return [{"label": "Register temporary residence", "text": "I want to register temporary residence"},
                {"label": "Renew temporary residence", "text": "I want to renew temporary residence"}]
    return [{"label": "Đăng ký tạm trú lần đầu", "text": "Tôi muốn đăng ký tạm trú"},
            {"label": "Gia hạn tạm trú", "text": "Tôi muốn gia hạn tạm trú"}]


def response(language: Language, state: str, key: str, code=None, with_choices=False, **values):
    return {"state": state, "reply": MESSAGES[language][key].format(**values),
            "candidate_code": code, "choices": choices(language) if with_choices else [],
            "reviewed_lookup_available": False, "language": language,
            "speech_language": SPEECH_LANGUAGES[language]}
