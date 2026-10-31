"""Real in-memory rendering and refusal cases; no network or personal fixtures."""

from dataclasses import replace
from hashlib import sha256

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pymupdf
import pytest

from hoso_api.forms.render import (
    DEMO_TEMPLATE, PAGE_HEIGHT, PAGE_WIDTH, SYNTHETIC_NOTICE,
    FontUnavailableError, RenderValidationError, ReviewStamp, TemplateSpec,
    discover_font_path, load_font, mapping_hash, measure_values, preview_png, render_pdf,
)
from hoso_api.forms.routes import create_router


FAKE_VALUES = {
    "full_name": "Nguyễn Thị Ánh Dương",
    "date_of_birth": "1995-06-15",
    "nationality": "Việt Nam",
    "address": "12 Đường Minh Họa, Phường Dữ Liệu Giả, Thành phố Mẫu",
    "phone_number": "+84 000 000 000",
    "email": "demo@example.invalid",
}


def client(enabled=True, **kwargs):
    app = FastAPI()
    app.include_router(create_router(demo_enabled=enabled, **kwargs))
    return TestClient(app)


def payload(**updates):
    return {"values": FAKE_VALUES, "revision": 2, "acknowledged": False,
            "template_version": DEMO_TEMPLATE.version, **updates}


def test_unicode_pdf_and_png_share_the_rendered_document():
    pdf = render_pdf(DEMO_TEMPLATE, FAKE_VALUES)
    assert pdf.startswith(b"%PDF")
    with pymupdf.open(stream=pdf, filetype="pdf") as document:
        assert len(document) == 1
        assert document[0].rect.width == pytest.approx(PAGE_WIDTH, abs=0.01)
        assert document[0].rect.height == pytest.approx(PAGE_HEIGHT, abs=0.01)
        text = document[0].get_text()
        assert FAKE_VALUES["full_name"] in text
        assert FAKE_VALUES["address"] in text
        assert "SYNTHETIC DEMO" in text
        assert "NOT AN OFFICIAL FORM" in text
        assert document.metadata["title"] == SYNTHETIC_NOTICE
        expected_png = document[0].get_pixmap(dpi=120, alpha=False).tobytes("png")
    assert preview_png(pdf) == expected_png


def test_all_value_geometry_is_padded_and_above_dotted_rules():
    font, _ = load_font()
    lines = measure_values(DEMO_TEMPLATE, FAKE_VALUES, font)
    layouts = {field.id: field for field in DEMO_TEMPLATE.fields}
    for line in lines:
        field = layouts[line.field]
        assert line.x >= field.x + field.padding
        assert line.x + line.width <= field.x + field.width - field.padding + 0.001
        assert line.bottom <= line.rule_y - 3 + 0.001
        assert line.top >= 0
        assert line.baseline < line.rule_y
    pdf = render_pdf(DEMO_TEMPLATE, FAKE_VALUES)
    with pymupdf.open(stream=pdf, filetype="pdf") as document:
        spans = [span for block in document[0].get_text("dict")["blocks"] if "lines" in block
                 for textline in block["lines"] for span in textline["spans"]]
        for line in lines:
            span = next(span for span in spans if span["text"] == line.text)
            assert span["bbox"][3] <= line.rule_y - 2.9
            assert span["origin"][1] == pytest.approx(line.baseline, abs=0.01)


def test_address_wraps_only_inside_allowed_lines():
    font, _ = load_font()
    values = {**FAKE_VALUES, "address": "Địa chỉ minh họa " * 11}
    lines = [line for line in measure_values(DEMO_TEMPLATE, values, font) if line.field == "address"]
    assert 1 < len(lines) <= 3
    assert " ".join(line.text for line in lines) == values["address"].strip()


@pytest.mark.parametrize("field,value,code", [
    ("full_name", "W" * 110, "text_overflow"),
    ("address", "W" * 290, "text_overflow"),
    ("full_name", "Name\nOther", "single_line_required"),
    ("full_name", "Demo \U0001f9ec", "unsupported_glyph"),
])
def test_renderer_rejects_overflow_and_unsupported_input(field, value, code):
    with pytest.raises(RenderValidationError) as error:
        render_pdf(DEMO_TEMPLATE, {**FAKE_VALUES, field: value})
    assert error.value.code == code
    assert error.value.field == field


def test_unknown_values_and_out_of_bounds_layout_fail_closed():
    with pytest.raises(RenderValidationError, match="unknown_field"):
        render_pdf(DEMO_TEMPLATE, {**FAKE_VALUES, "arbitrary": "x"})
    invalid = replace(DEMO_TEMPLATE, fields=(replace(DEMO_TEMPLATE.fields[0], x=-10),))
    with pytest.raises(RenderValidationError, match="invalid_template_geometry"):
        render_pdf(invalid, {"full_name": "Demo"})


def test_null_profile_values_render_as_blank_without_invented_answers():
    pdf = render_pdf(DEMO_TEMPLATE, dict.fromkeys(FAKE_VALUES))
    with pymupdf.open(stream=pdf, filetype="pdf") as document:
        text = document[0].get_text()
        assert "None" not in text
        assert FAKE_VALUES["full_name"] not in text
        assert "Họ và tên" in text


def test_explicit_missing_font_does_not_silently_substitute(monkeypatch):
    monkeypatch.setenv("HOSO_FORM_FONT_PATH", "/deliberately-not-present/hoso.ttf")
    with pytest.raises(FontUnavailableError):
        discover_font_path()


def test_review_binds_source_pdf_and_mapping_hashes():
    pdf = render_pdf(DEMO_TEMPLATE, {})
    source_hash = "a" * 64
    review = ReviewStamp(source_hash, sha256(pdf).hexdigest(), mapping_hash(DEMO_TEMPLATE.fields),
                         "human reviewer fixture", "2026-10-31T00:00:00Z")
    template = TemplateSpec("fixture", "v1", DEMO_TEMPLATE.fields, source_sha256=source_hash,
                            pdf_bytes=pdf, review=review)
    assert template.has_current_review()
    assert not replace(template, source_sha256="b" * 64).has_current_review()
    assert not replace(template, pdf_bytes=pdf + b"changed").has_current_review()
    changed_mapping = (replace(template.fields[0], padding=8), *template.fields[1:])
    assert not replace(template, fields=changed_mapping).has_current_review()


def test_synthetic_demo_is_disabled_by_default_and_unknown_templates_are_hidden():
    assert client(False).get("/v1/forms/demo").status_code == 404
    assert client().get("/v1/forms/unknown").status_code == 404
    assert client().post("/v1/forms/unknown/pdf", json=payload(acknowledged=True)).status_code == 404


def test_draft_real_template_cannot_be_used_on_any_route():
    draft = TemplateSpec("draft", "v1", DEMO_TEMPLATE.fields)
    api = client(templates={"draft": draft})
    assert api.get("/v1/forms/draft").status_code == 409
    for route in ["preview", "pdf"]:
        response = api.post(f"/v1/forms/draft/{route}", json=payload(acknowledged=True))
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "template_not_reviewed"


def test_metadata_preview_acknowledgement_and_download_contract():
    api = client()
    metadata = api.get("/v1/forms/demo").json()
    assert metadata["synthetic"] is True
    assert metadata["coordinate_origin"].startswith("top-left")
    assert metadata["page_numbering"] == "zero-based"
    assert {field["id"] for field in metadata["fields"]} == set(FAKE_VALUES)
    preview = api.post("/v1/forms/demo/preview", json=payload())
    assert preview.status_code == 200
    assert preview.headers["content-type"] == "image/png"
    assert preview.content.startswith(b"\x89PNG")
    assert preview.headers["cache-control"] == "no-store, private"
    assert preview.headers["x-form-revision"] == "2"
    refused = api.post("/v1/forms/demo/pdf", json=payload())
    assert refused.status_code == 422
    assert refused.json()["detail"]["code"] == "review_acknowledgement_required"
    download = api.post("/v1/forms/demo/pdf", json=payload(acknowledged=True))
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/pdf"
    assert download.headers["x-template-version"] == DEMO_TEMPLATE.version
    assert download.content.startswith(b"%PDF")


def test_changed_template_overflow_and_unknown_fields_return_validation_errors():
    api = client()
    assert api.post("/v1/forms/demo/preview", json=payload(template_version="old")).status_code == 409
    overflow = api.post("/v1/forms/demo/preview", json=payload(values={"full_name": "W" * 110}))
    assert overflow.status_code == 422
    assert overflow.json()["detail"] == {"code": "text_overflow", "field": "full_name"}
    assert api.post("/v1/forms/demo/preview", json=payload(values={"not_allowed": "x"})).status_code == 422
    assert api.post("/v1/forms/demo/preview", json=payload(revision=-1)).status_code == 422
