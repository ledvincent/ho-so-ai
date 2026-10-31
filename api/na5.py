"""Compatibility helpers for the original NA5 workflow. New clients use document IDs."""
from api.config import ROOT
from api import form_engine
from api.form_registry import get_document

SPEC_PATH = ROOT/'data/forms/NA5/workflow.json'
FONT_PATH = form_engine.FONT_PATH


def spec():
    return get_document('na5-provincial-stay-extension').mapping


active = form_engine.active
template_digest = form_engine.template_digest
page_previews = form_engine.page_previews


def validate(values, *, partial=False):
    return form_engine.validate(values,spec(),partial=partial)


def render(values,draft=True):
    return form_engine.render(values,spec(),draft=draft)


def token(values):
    return form_engine.token(values,spec())


def verify_token(values,value):
    return form_engine.verify_token(values,value,spec())
