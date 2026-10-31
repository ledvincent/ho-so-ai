"""Prepare cited source sections for answer generation; never grant evidence access."""
import re


def focus_evidence(evidence, query):
    from api.rag import normalize
    text = normalize(query)
    if re.search(r'walk me through|fill|dien|help.*form', text):
        return present_evidence(evidence)
    if re.search(r'fee|cost|price|how much|le phi|chi phi', text):
        sections = ('phi', 'cach thuc', 'trinh tu')
        forms = False
    elif re.search(r'how long|processing|thoi han|bao lau|duration', text):
        sections = ('cach thuc', 'thoi han', 'thoi gian giai quyet')
        forms = False
    elif re.search(r'edition|revision|phien ban|mau nao', text):
        sections = ('thanh phan',)
        forms = 'headers'
    elif re.search(r'document|require|checklist|intended for|eligible|ho so|giay to', text):
        sections = ('thanh phan', 'yeu cau', 'doi tuong')
        forms = 'instructions'
    elif re.search(r'steps|trinh tu|quy trinh', text):
        sections = ('trinh tu', 'cach thuc')
        forms = False
    else:
        return present_evidence(evidence)
    procedure_name = normalize(evidence.sources[0].title.split(' — ')[0]) if evidence.sources else ''
    stay_only = 'gia han tam tru' in procedure_name and not procedure_name.startswith('cap thi thuc')
    if forms == 'instructions' and stay_only:
        forms = 'headers'
    result = present_evidence(evidence)
    kept = []
    kept_locators = set()
    review = result.sources[0].evidence_status if result.sources else {}
    for source in result.sources:
        units = re.split(r'(?m)(?=^(?:section:\d+:[^\n]+|page:\d+)\n)', source.text)
        if '| form:' in source.title:
            selected = []
            if forms:
                for unit in units:
                    lines = unit.splitlines()
                    if not lines: continue
                    indices = set()
                    for index, line in enumerate(lines):
                        if re.search(r'thong tu|circular|mau \(form\)|mau na5|/20\d{2}/tt-bca', normalize(line)):
                            indices.update(range(max(1, index-1), min(len(lines), index+4)))
                    if forms == 'instructions':
                        start = next((i for i, line in enumerate(lines) if re.search(r'^\s*(ghi chu|notes|\(1\))', normalize(line))), None)
                        if start is not None: indices.update(range(start, len(lines)))
                    if indices:
                        selected.append(lines[0] + '\n' + '\n'.join(lines[i] for i in sorted(indices)) + '\n\n')
                if not selected:
                    selected = units
        else:
            selected = [unit for unit in units if any(term in normalize(unit.split('\n', 1)[0]) for term in sections)]
        if selected:
            kept.append(source.model_copy(update={'text': ''.join(selected), 'evidence_status': {},
                'title': source.title.replace('complete captured source', 'complete relevant sections')}))
            kept_locators.update((source.id, unit.split('\n', 1)[0]) for unit in selected if unit)
    # Never silently drop every source when a new corpus uses different labels.
    if not kept:
        return result
    review = dict(review)
    review['conflicts'] = [conflict for conflict in review.get('conflicts', [])
        if any((ref.get('source_id'), ref.get('locator')) in kept_locators for ref in conflict.get('sources', []))]
    if stay_only and forms == 'headers':
        review['conflicts'] = [conflict for conflict in review['conflicts']
            if not re.search(r'thi thuc roi|separate visa', normalize(conflict.get('summary') or ''))]
    kept[0].evidence_status = review
    return result.model_copy(update={'sources': kept})


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
