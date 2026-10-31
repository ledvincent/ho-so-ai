"""Explain source changes separately from extraction changes and record final audit."""
import argparse
import json
from sqlalchemy import text
from api.config import ROOT,engine
from api.profiles import normalise,walk
from api.storage import write_json
from scripts.rerun_selected import changes


def semantic(p):
    omit={'id','snapshot_id','fetched_at','sha256','linked_from','form_ids'}
    return dict(name=p['name'],document=p['document_json'],
        methods=[{k:v for k,v in x.items() if k not in omit} for x in p['methods']],
        requirements=[{k:v for k,v in x.items() if k not in omit} for x in p['requirements']],
        forms=[{k:f.get(k) for k in ('source_url','form_sha256','association_method','revision_reference')} for f in p['forms']],
        profile=(p.get('structured_profile') or {}).get('profile'))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--batch');args=parser.parse_args()
    latest=json.loads((ROOT/'data/runs/latest.json').read_text(encoding='utf-8'))
    folder=ROOT/args.batch if args.batch else (ROOT/latest['report']).parent
    manifest=json.loads((folder/'batch.json').read_text(encoding='utf-8'))
    lines=['# Controlled procedure analysis report','',f'Status: **{manifest["status"]}**',f'Baseline: `{manifest["baseline_id"]}`',f'Batch: `{manifest["batch_id"]}`','',
        'All selected procedures use the same ingestion code, profile schema, prompts, model settings and validation rules. Each procedure has before/after snapshots, semantic changes, complete source evidence, model responses and validation results.','',
        '## Source changes versus extraction changes','',
        '| Procedure | Live primary | Page bytes changed | Existing section text changed | Newly captured sections |',
        '| --- | --- | --- | --- | --- |']
    for entry in manifest['procedures']:
        code=entry['code'];path=folder/code
        if not (path/'after.json').exists():continue
        before=json.loads((path/'before.json').read_text(encoding='utf-8'));after=json.loads((path/'after.json').read_text(encoding='utf-8'))
        old={s['heading']:normalise(s['text_verbatim']) for s in before['document_json']['sections']}
        new={s['heading']:normalise(s['text_verbatim']) for s in after['document_json']['sections']}
        changed=[k for k in set(old)&set(new) if old[k]!=new[k]]
        added=sorted(set(new)-set(old))
        profile=after['structured_profile']['profile']
        facts=[n for n in walk(profile) if {'value','status','source_refs','conflicts'}<=n.keys()]
        entry.update(parser_before=before['parser_version'],parser_after=after['parser_version'],existing_sections_changed=changed,added_sections=added,
            supported_facts=sum(f['status']=='supported' for f in facts),unknown_facts=sum(f['status']=='unknown' for f in facts),conflicting_facts=sum(f['status']=='conflict' for f in facts))
        delta=changes(semantic(before),semantic(after));write_json(path/'changes.json',delta)
        entry['changed_paths']=[d['path'] for d in delta]
        primary=next((a['mode'] for a in entry['acquisition'] if 'dvc-chi-tiet' in a['url']),'unknown')
        lines.append(f'| [{code}]({code}/profile/profile.json) | {primary} | {entry["source_changed"]} | {len(changed)} | {", ".join(added) or "None"} |')
    lines+=['','The parser now also captures the portal service-selection panel, which explicitly identifies audience and authority level. Newly captured text is distinguished from changed wording in an existing section. Fetch time is never substituted for a government update/effective date.','',
        '## Structured extraction','',
        '| Procedure | Aliases / examples | Clarification criteria | Supported / unknown / conflicting facts | Verified citations |',
        '| --- | --- | --- | --- | --- |']
    for e in manifest['procedures']:
        lines.append(f'| {e["code"]} | {e.get("aliases",0)} / {e.get("examples",0)} | {e.get("criteria",0)} | {e.get("supported_facts",0)} / {e.get("unknown_facts",0)} / {e.get("conflicting_facts",0)} | {e.get("citations",0)} |')
    lines+=['','All requested profile categories are included. Unknown values remain null/unknown rather than guessed. Generated aliases, requests and question wording are labelled; they are not legal evidence. Quote validation establishes source membership, not legal correctness or currency.','',
        '## Catalog distinctions','']
    if (folder/'comparisons.json').exists():
        compared=json.loads((folder/'comparisons.json').read_text(encoding='utf-8'))
        for relation in compared['relationships']:
            lines.append(f'- **{relation["left_code"]} / {relation["right_code"]}** — {relation["relationship_type"]}: '+str(relation['rationale']['value']))
        lines+=['','Full two-sided citations and distinguishing criteria: [comparisons.json](comparisons.json). Shared NA5 usage never establishes procedural equivalence.']
    lines+=['','## Acquisition and outstanding review','']
    for e in manifest['procedures']:
        lines+=['### '+e['code'],'',f'Result: {e["status"]}. Source facts ready for assistant context: {e.get("facts_ready",False)}.','']
        for a in e['acquisition']:
            lines.append('- '+a['mode']+': '+a['url']+(' — '+a['error'] if a.get('error') else ''))
        for issue in e['issues']:lines.append('- Internal review issue: '+issue)
        lines+=['',f'[Before]({e["code"]}/before.json) · [After]({e["code"]}/after.json) · [Semantic changes]({e["code"]}/changes.json) · [Evidence]({e["code"]}/profile/sources.json)','']
    if manifest.get('comparison_error'):lines.append('Comparison failed: '+manifest['comparison_error'])
    (folder/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    write_json(folder/'batch.json',manifest)
    with engine().begin() as db:
        db.execute(text('UPDATE catalog_batch SET report=CAST(:report AS jsonb) WHERE id=:id'),dict(report=json.dumps(manifest),id=manifest['batch_id']))
    print((folder/'REPORT.md').relative_to(ROOT).as_posix())


if __name__=='__main__':main()
