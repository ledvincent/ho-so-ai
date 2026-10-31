"""Prepare cited source sections for answer generation; never grant evidence access."""


def present_evidence(evidence):
    """Keep every original source body, with concise, explicitly mapped review notes."""
    from api.assistant import Retrieval, Source
    originals = list(evidence.sources)
    def role(s):
        if ' — primary — ' in s.title: return 'primary'
        if ' — supplementary — ' in s.title: return 'supplementary'
        if ' — form:' in s.title: return s.title.split(' — ')[1]
        return 'source'
    ordered = sorted(originals, key=lambda s: ({'primary': 0, 'supplementary': 1}.get(role(s), 2), s.id))
    aliases = {s.id: f's{i+1}' for i, s in enumerate(ordered)}
    role_ids = {role(s): aliases[s.id] for s in ordered}
    review = next((s.evidence_status for s in originals if s.evidence_status), {})
    summary = {k: review[k] for k in ('access', 'procedure_currency', 'form_applicability') if k in review}
    summary['source_id_map'] = {aliases[s.id]: s.id for s in ordered}
    summary['conflicts'] = []
    for conflict in review.get('conflicting_claims', []):
        refs = [dict(source_id=role_ids.get(r.get('source_id'), r.get('source_id')), locator=r.get('locator'), quote=r.get('quote'))
                for r in conflict.get('source_refs', [])]
        summary['conflicts'].append(dict(summary=conflict.get('value'), uncertainty=conflict.get('conflicts', []), sources=refs))
    summary['notice'] = 'Review notes flag uncertainty; procedural facts must be checked against the original text below. Neither source order nor the primary label resolves conflicts.'
    sources = [Source(id=aliases[s.id], title=(s.title if role(s)=='source' else s.title.split(' — ')[0] + ' | ' + role(s) + ' | complete captured source'),
               url=s.url, text=s.text, evidence_status=summary if i == 0 else {}) for i, s in enumerate(ordered)]
    data = evidence.model_dump(mode='json')
    data['sources'] = [s.model_dump(mode='json') for s in sources]
    return Retrieval.model_validate(data)
