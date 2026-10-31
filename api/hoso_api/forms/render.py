"""Measured Unicode text above dotted rules, with no filesystem input from HTTP.

This is a renderer seam, not a CT01/NA5 mapping or an official-template approval.
All coordinates use unrotated PDF points from the top-left (x right, y down).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import unicodedata
from typing import Mapping

import pymupdf

from .schemas import FieldMetadata, FormMetadata


SYNTHETIC_NOTICE = "SYNTHETIC DEMO - NOT AN OFFICIAL FORM"
PAGE_WIDTH = 595.276
PAGE_HEIGHT = 841.89
FONT_NAME = "hoso_unicode"
VIETNAMESE_PROBE = "Nguyễn Thị Bích Hằng Đặng Quốc Việt ă â ê ô ơ ư đ Ắ Ặ Ế Ệ Ớ Ợ Ứ Ự"


class RenderValidationError(ValueError):
    """Safe, field-level errors without echoing request values."""

    def __init__(self, code: str, field: str | None = None):
        self.code = code
        self.field = field
        super().__init__(code)


class FontUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class FieldLayout:
    id: str
    label: str
    max_length: int
    rule_y: tuple[float, ...]
    page: int = 0
    x: float = 52
    width: float = PAGE_WIDTH - 104
    padding: float = 5
    font_size: float = 11
    rule_clearance: float = 3


DEMO_FIELDS = (
    FieldLayout("full_name", "Họ và tên / Full name", 120, (214,)),
    FieldLayout("date_of_birth", "Ngày sinh / Date of birth", 10, (284,)),
    FieldLayout("nationality", "Quốc tịch / Nationality", 80, (354,)),
    FieldLayout("address", "Địa chỉ / Address", 300, (424, 452, 480)),
    FieldLayout("phone_number", "Số điện thoại / Phone number", 32, (550,)),
    FieldLayout("email", "Email", 254, (620,)),
)


def mapping_hash(fields: tuple[FieldLayout, ...]) -> str:
    return sha256(json.dumps([asdict(field) for field in fields], sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class ReviewStamp:
    source_sha256: str
    pdf_sha256: str
    mapping_sha256: str
    reviewed_by: str
    reviewed_at: str


@dataclass(frozen=True)
class TemplateSpec:
    id: str
    version: str
    fields: tuple[FieldLayout, ...]
    synthetic: bool = False
    source_sha256: str | None = None
    pdf_bytes: bytes | None = None
    review: ReviewStamp | None = None

    def has_current_review(self) -> bool:
        """A changed source, PDF or mapping invalidates the human review."""
        if not self.review or not self.pdf_bytes or not self.source_sha256:
            return False
        return bool(
            self.review.reviewed_by.strip()
            and self.review.reviewed_at.strip()
            and self.review.source_sha256 == self.source_sha256
            and self.review.pdf_sha256 == sha256(self.pdf_bytes).hexdigest()
            and self.review.mapping_sha256 == mapping_hash(self.fields)
        )


DEMO_TEMPLATE = TemplateSpec("demo", "synthetic-demo-v1", DEMO_FIELDS, synthetic=True)


def discover_font_path() -> Path:
    """An explicit Unicode font is embedded; missing fonts never fall back to Helvetica."""
    configured = os.environ.get("HOSO_FORM_FONT_PATH")
    candidates = [Path(configured)] if configured else [
        Path(__file__).resolve().parents[3] / "assets" / "fonts" / "DejaVuSans.ttf",
        Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "native" / "poppler" / "Library" / "share" / "fonts" / "DejaVuSans.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
        Path("C:/Windows/Fonts/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path.is_file():
            font = pymupdf.Font(fontfile=str(path))
            # Some system fonts alias space/hyphen glyphs to other codepoints;
            # MuPDF then emits NBSP/soft hyphen on copy/extraction. Refuse them.
            aliases = ((" ", "\u00a0"), (" ", "\u202f"), ("-", "\u00ad"), ("-", "\u2010"), ("-", "\u2011"))
            ambiguous = any(font.has_glyph(ord(left), fallback=False) == font.has_glyph(ord(right), fallback=False)
                            for left, right in aliases if font.has_glyph(ord(right), fallback=False))
            if not ambiguous and all(font.has_glyph(ord(character), fallback=False) for character in VIETNAMESE_PROBE):
                return path
    raise FontUnavailableError("Set HOSO_FORM_FONT_PATH to DejaVu Sans or a font with Vietnamese coverage and unambiguous Unicode mappings.")


def load_font() -> tuple[pymupdf.Font, bytes]:
    data = discover_font_path().read_bytes()
    font = pymupdf.Font(fontbuffer=data)
    fixed_text = "Hồ sơ cá nhân Bản xem trước minh họa HỒ SƠ AI" + "".join(field.label for field in DEMO_FIELDS)
    if any(not font.has_glyph(ord(character), fallback=False) for character in fixed_text):
        raise FontUnavailableError("Configured font does not cover the demonstration labels.")
    return font, data


@dataclass(frozen=True)
class PlacedLine:
    field: str
    page: int
    text: str
    x: float
    baseline: float
    width: float
    top: float
    bottom: float
    rule_y: float
    font_size: float


def _normalise(value: str, field: FieldLayout, font: pymupdf.Font) -> str:
    value = unicodedata.normalize("NFC", value)
    if len(value) > field.max_length:
        raise RenderValidationError("max_length", field.id)
    if any(unicodedata.category(char) in {"Cc", "Cf", "Cs"} and char not in "\n\t" for char in value):
        raise RenderValidationError("unsupported_character", field.id)
    if field.id != "address" and ("\n" in value or "\t" in value):
        raise RenderValidationError("single_line_required", field.id)
    value = value.replace("\t", " ")
    if any(not font.has_glyph(ord(char), fallback=False) for char in value if char != "\n"):
        raise RenderValidationError("unsupported_glyph", field.id)
    return value


def _wrap(text: str, width: float, font: pymupdf.Font, size: float, field_id: str) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        current = ""
        for word in paragraph.split():
            if font.text_length(word, fontsize=size) > width:
                raise RenderValidationError("text_overflow", field_id)
            candidate = f"{current} {word}" if current else word
            if font.text_length(candidate, fontsize=size) <= width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def measure_values(template: TemplateSpec, values: Mapping[str, str | None], font: pymupdf.Font) -> tuple[PlacedLine, ...]:
    allowed = {field.id for field in template.fields}
    if set(values) - allowed:
        raise RenderValidationError("unknown_field")
    placed: list[PlacedLine] = []
    for field in template.fields:
        geometry = (field.x, field.width, field.padding, field.font_size, field.rule_clearance, *field.rule_y)
        if not all(math.isfinite(number) for number in geometry):
            raise RenderValidationError("invalid_template_geometry", field.id)
        if field.page != 0 or field.x < 0 or field.padding < 0 or field.width <= 2 * field.padding or field.x + field.width > PAGE_WIDTH:
            raise RenderValidationError("invalid_template_geometry", field.id)
        if not field.rule_y or field.rule_clearance < 2 or field.font_size <= 0:
            raise RenderValidationError("invalid_template_geometry", field.id)
        minimum_spacing = (font.ascender - font.descender) * field.font_size + field.rule_clearance
        if any(right - left < minimum_spacing for left, right in zip(field.rule_y, field.rule_y[1:])):
            raise RenderValidationError("invalid_template_geometry", field.id)
        available = field.width - 2 * field.padding
        text = _normalise(values.get(field.id) or "", field, font)
        if len(field.rule_y) == 1:
            if font.text_length(text, fontsize=field.font_size) > available:
                raise RenderValidationError("text_overflow", field.id)
            lines = [text]
        else:
            lines = _wrap(text, available, font, field.font_size, field.id)
        if len(lines) > len(field.rule_y):
            raise RenderValidationError("text_overflow", field.id)
        for text_line, rule_y in zip(lines, field.rule_y):
            # Account for descenders: the entire font box ends above the dotted rule.
            baseline = rule_y - field.rule_clearance - max(0, -font.descender) * field.font_size
            top = baseline - font.ascender * field.font_size
            bottom = baseline + max(0, -font.descender) * field.font_size
            if top < 0 or rule_y > PAGE_HEIGHT - 32 or bottom > rule_y - field.rule_clearance + 0.001:
                raise RenderValidationError("invalid_template_geometry", field.id)
            placed.append(PlacedLine(field.id, field.page, text_line, field.x + field.padding, baseline,
                                     font.text_length(text_line, fontsize=field.font_size), top, bottom,
                                     rule_y, field.font_size))
    return tuple(placed)


def _insert(page: pymupdf.Page, x: float, baseline: float, text: str, size: float, color: tuple[float, float, float]) -> None:
    page.insert_text((x, baseline), text, fontname=FONT_NAME, fontsize=size, color=color)


def _draw_demo(page: pymupdf.Page, template: TemplateSpec) -> None:
    navy = (0.10, 0.20, 0.24)
    muted = (0.35, 0.41, 0.43)
    page.draw_rect(pymupdf.Rect(34, 32, PAGE_WIDTH - 34, 94), color=None, fill=(0.98, 0.92, 0.77))
    _insert(page, 48, 58, "SYNTHETIC DEMO", 17, navy)
    _insert(page, 48, 80, "NOT AN OFFICIAL FORM - USE FICTIONAL DATA ONLY", 10, navy)
    _insert(page, 52, 136, "Hồ sơ cá nhân", 24, navy)
    _insert(page, 52, 157, "Bản xem trước minh họa / Demonstration review copy", 10, muted)
    for field in template.fields:
        _insert(page, field.x, field.rule_y[0] - 30, field.label, 10, muted)
        for y in field.rule_y:
            page.draw_line((field.x, y), (field.x + field.width, y), color=(0.54, 0.59, 0.58), width=0.6, dashes="[1 3] 0")
    page.draw_line((52, 680), (PAGE_WIDTH - 52, 680), color=(0.85, 0.87, 0.85), width=0.5)
    _insert(page, 52, 704, "SYNTHETIC DEMO - NOT AN OFFICIAL FORM", 10, muted)
    _insert(page, 52, 724, "No government submission. Preview and PDF use the same renderer.", 9, muted)
    _insert(page, 52, 784, "HỒ SƠ AI / FORM RENDERER DEMO", 8, muted)
    _insert(page, PAGE_WIDTH - 91, 784, "01 / 01", 8, muted)


def render_pdf(template: TemplateSpec, values: Mapping[str, str | None]) -> bytes:
    font, font_data = load_font()
    lines = measure_values(template, values, font)
    if template.synthetic:
        document = pymupdf.open()
        page = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    else:
        if not template.has_current_review():
            raise RenderValidationError("template_not_reviewed")
        document = pymupdf.open(stream=template.pdf_bytes, filetype="pdf")
        if len(document) != 1 or document[0].rotation != 0 or abs(document[0].rect.width - PAGE_WIDTH) > 0.1 or abs(document[0].rect.height - PAGE_HEIGHT) > 0.1:
            document.close()
            raise RenderValidationError("unsupported_template_geometry")
        page = document[0]
    try:
        page.insert_font(fontname=FONT_NAME, fontbuffer=font_data)
        if template.synthetic:
            _draw_demo(page, template)
        for line in lines:
            if line.text:
                _insert(page, line.x, line.baseline, line.text, line.font_size, (0.08, 0.16, 0.20))
        document.set_metadata({"title": SYNTHETIC_NOTICE if template.synthetic else "Reviewed form", "producer": "Ho So AI transient renderer"})
        document.subset_fonts()
        return document.tobytes(garbage=4, deflate=True)
    finally:
        document.close()


def preview_png(pdf_bytes: bytes) -> bytes:
    """Rasterize the exact PDF result, rather than independently laying out a preview."""
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
        return document[0].get_pixmap(dpi=120, alpha=False).tobytes("png")


def template_metadata(template: TemplateSpec) -> FormMetadata:
    return FormMetadata(
        id=template.id,
        template_version=template.version,
        title="Dossier personnel - démonstration" if template.synthetic else "Reviewed form",
        synthetic=template.synthetic,
        source="synthetic" if template.synthetic else "reviewed",
        review_status="synthetic_demo" if template.synthetic else "reviewed",
        notice=SYNTHETIC_NOTICE if template.synthetic else "Human-reviewed template; verify your entered values before download.",
        pages=[{"page": 0, "width": PAGE_WIDTH, "height": PAGE_HEIGHT}],
        fields=[FieldMetadata(**asdict(field), type={"date_of_birth": "date", "email": "email", "phone_number": "tel"}.get(field.id, "text")) for field in template.fields],
    )
