"""Conservative public-question gate, not a general PII detector.

Block rather than guess how to remove personal fields. No blocked text is kept.
Audio has already reached the voice provider; this gate protects the RAG hop.
"""
import re
import unicodedata


def contains_personal_details(text):
    value = ''.join(c for c in unicodedata.normalize('NFKD', text)
                    if not unicodedata.combining(c)).lower().replace('đ', 'd')
    patterns = (
        r'\b[^\s@]+@[^\s@]+\.[a-z]{2,}\b',
        r'(?<!\w)(?:\+?\d[\s().-]?){9,}(?!\w)',
        r'\b[a-z]{1,3}\d{6,12}\b',
        r'\b(?:my name is|my full name|i am called|ten (?:toi|minh|em) la|toi ten|ho ten (?:la|cua))\b',
        r'\b(?:my address|i live at|dia chi (?:cua|la)|toi o so|minh o so)\b',
        r'\b(?:my (?:passport|visa|phone|telephone|id) (?:number|is)|so (?:ho chieu|dien thoai|cccd|cmnd) (?:cua|la))\b',
        r'\b(?:born on|date of birth|ngay sinh|sinh ngay)\b',
        r'\b(?:password|api[ _-]?key|mat khau|bearer|sk-[a-z0-9])\b',
        r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b|\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b',
    )
    return any(re.search(pattern, value) for pattern in patterns)
