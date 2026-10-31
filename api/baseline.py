"""Immutable analysis contract shared by single-URL and catalog ingestion."""
import hashlib
import json
import os
from sqlalchemy import text
from api.config import ROOT,engine
from api import profiles,field_mapping


def contract():
    from api.comparisons import PROMPT as compare_prompt,ComparisonSet
    files=['api/analysis.py','api/procedure_sources.py','api/form_catalog.py','api/form_recovery.py','api/profiles.py','api/field_mapping.py','api/comparisons.py','api/parse.py','api/attachments.py','api/documents.py']
    configuration=dict(version='procedure-baseline-1',provider=os.getenv('FIELD_MAPPING_PROVIDER','openai'),
        model=os.getenv('PROFILE_MODEL',os.getenv('FIELD_MAPPING_MODEL','gpt-6-astra')),
        reasoning_effort=os.getenv('PROFILE_REASONING','high'),
        field_model=os.getenv('FIELD_MAPPING_MODEL','gpt-6-astra'),field_reasoning=os.getenv('FIELD_MAPPING_REASONING','high'),
        model_output_tokens=field_mapping.MODEL_OUTPUT_TOKENS,model_retry_output_tokens=field_mapping.MODEL_RETRY_OUTPUT_TOKENS,
        profile_version=profiles.VERSION,profile_schema_sha256=profiles.digest(profiles.Profile.model_json_schema()),
        profile_prompt_sha256=hashlib.sha256(profiles.PROMPT.encode()).hexdigest(),
        field_mapping_version=field_mapping.VERSION,field_schema_sha256=profiles.digest(field_mapping.Mapping.model_json_schema()),
        field_prompt_sha256=hashlib.sha256(field_mapping.PROMPT.encode()).hexdigest(),
        comparison_schema_sha256=profiles.digest(ComparisonSet.model_json_schema()),comparison_prompt_sha256=hashlib.sha256(compare_prompt.encode()).hexdigest(),
        criterion_vocabulary=profiles.CRITERIA,
        retrieval_policy='Attempt live primary, supplementary pages and each attachment. Replay explicitly identified last-known evidence on failure; never relabel replay as a fresh fetch.',
        association_policy='Successful exact fingerprint takes precedence; filename fallback only without a successful download.',
        validations=['strict schema','exact identity','verbatim citation membership','condition structure','known form hashes','unknown is not ineligible'],
        source_code_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files})
    configuration['profile_validation_attempts']=2
    return dict(id=profiles.digest(configuration),**configuration)


def ensure():
    baseline=contract();folder=ROOT/'data/baselines'/baseline['id'];folder.mkdir(parents=True,exist_ok=True)
    content=json.dumps(baseline,ensure_ascii=False,indent=2)
    path=folder/'manifest.json'
    if path.exists() and path.read_text(encoding='utf-8')!=content:raise ValueError('Baseline manifest is immutable')
    path.write_text(content,encoding='utf-8')
    (folder/'profile.schema.json').write_text(json.dumps(profiles.Profile.model_json_schema(),indent=2),encoding='utf-8')
    (folder/'profile-prompt.txt').write_text(profiles.PROMPT,encoding='utf-8')
    (folder/'field-mapping-prompt.txt').write_text(field_mapping.PROMPT,encoding='utf-8')
    from api.comparisons import PROMPT as comparison_prompt,ComparisonSet
    (folder/'comparison-prompt.txt').write_text(comparison_prompt,encoding='utf-8')
    (folder/'comparison.schema.json').write_text(json.dumps(ComparisonSet.model_json_schema(),indent=2),encoding='utf-8')
    (folder/'field-mapping.schema.json').write_text(json.dumps(field_mapping.Mapping.model_json_schema(),indent=2),encoding='utf-8')
    # Keep the exact implementation, not only hashes that would become
    # unrecoverable after a later edit to an uncommitted local project.
    for relative,expected in baseline['source_code_sha256'].items():
        raw=(ROOT/relative).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Baseline source changed while archiving')
        target=folder/'source'/relative
        if target.exists() and target.read_bytes()!=raw:raise ValueError('Baseline source archive is immutable')
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(raw)
    with engine().begin() as db:
        db.execute(text('INSERT INTO analysis_baseline(id,configuration) VALUES (:id,CAST(:config AS jsonb)) ON CONFLICT DO NOTHING'),dict(id=baseline['id'],config=content))
    return baseline
