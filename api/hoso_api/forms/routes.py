"""Feature-gated, transient demo routes. No uploaded template paths or model calls."""

from collections.abc import Mapping

from fastapi import APIRouter, HTTPException, Response

from .render import DEMO_TEMPLATE, FontUnavailableError, RenderValidationError, TemplateSpec, preview_png, render_pdf, template_metadata
from .schemas import FormMetadata, FormRenderRequest


def create_router(demo_enabled: bool = False, *, templates: Mapping[str, TemplateSpec] | None = None) -> APIRouter:
    router = APIRouter(prefix="/v1/forms", tags=["forms"])
    # The registry is constructed by trusted server code, never from request fields.
    registry = dict(templates) if templates is not None else {"demo": DEMO_TEMPLATE}

    def resolve(template_id: str) -> TemplateSpec:
        template = registry.get(template_id)
        if template is None or (template.synthetic and not demo_enabled):
            raise HTTPException(404, detail={"code": "form_not_available"})
        if not template.synthetic and not template.has_current_review():
            raise HTTPException(409, detail={"code": "template_not_reviewed"})
        return template

    def generate(template: TemplateSpec, payload: FormRenderRequest) -> bytes:
        if payload.template_version != template.version:
            raise HTTPException(409, detail={"code": "template_version_changed"})
        try:
            return render_pdf(template, payload.values.model_dump())
        except RenderValidationError as error:
            raise HTTPException(422, detail={"code": error.code, "field": error.field}) from None
        except FontUnavailableError:
            raise HTTPException(503, detail={"code": "unicode_font_unavailable"}) from None

    def headers(template: TemplateSpec, payload: FormRenderRequest) -> dict[str, str]:
        return {
            "Cache-Control": "no-store, private",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
            "X-Form-Revision": str(payload.revision),
            "X-Template-Version": template.version,
        }

    @router.get("/{template_id}", response_model=FormMetadata)
    def get_form(template_id: str, response: Response) -> FormMetadata:
        response.headers["Cache-Control"] = "no-store, private"
        return template_metadata(resolve(template_id))

    @router.post("/{template_id}/preview")
    def preview(template_id: str, payload: FormRenderRequest) -> Response:
        template = resolve(template_id)
        pdf = generate(template, payload)
        return Response(preview_png(pdf), media_type="image/png", headers=headers(template, payload))

    @router.post("/{template_id}/pdf")
    def download(template_id: str, payload: FormRenderRequest) -> Response:
        template = resolve(template_id)
        if not payload.acknowledged:
            raise HTTPException(422, detail={"code": "review_acknowledgement_required"})
        pdf = generate(template, payload)
        response_headers = headers(template, payload)
        response_headers["Content-Disposition"] = 'attachment; filename="hoso-synthetic-demo.pdf"' if template.synthetic else 'attachment; filename="hoso-reviewed-form.pdf"'
        return Response(pdf, media_type="application/pdf", headers=response_headers)

    return router
