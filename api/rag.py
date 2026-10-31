"""Hybrid retrieval, scoped evidence and signed clarification state."""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import unicodedata
from functools import lru_cache

import httpx
from sqlalchemy import text
from api.config import engine
from api.rag_index import embed


def normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFD',value.lower().replace('đ','d')) if unicodedata.category(c)!='Mn')


STOP = set('i my me the a an to for is are do can please want need how what where which this that it of in on with toi muon can xin cho la cua va o tai nhung gi nao'.split())


def terms(query):
    return list(dict.fromkeys(t for t in re.findall(r'[a-z0-9]+',normalize(query)) if t not in STOP))[:30]


SCOPE = '''JOIN rag_member m ON m.release_id=i.release_id AND m.code=i.code
    JOIN procedure p ON p.code=m.code AND p.active AND p.current_snapshot_id=m.snapshot_id
    JOIN procedure_profile_head ph ON ph.snapshot_id=m.snapshot_id AND ph.profile_id=m.profile_id'''


def release_info(release=None):
    with engine().connect() as db:
        row=db.execute(text('''SELECT r.*,s.configuration FROM rag_release r
            JOIN embedding_space s ON s.id=r.space_id
            WHERE r.id=COALESCE(CAST(:r AS uuid),(SELECT release_id FROM rag_head WHERE singleton))
            AND r.status='published' '''),dict(r=release)).mappings().first()
        if not row: raise RuntimeError('No published retrieval index')
        return dict(row)


def fuse(branches):
    """One contribution per procedure per branch, irrespective of alias count."""
    scores={}
    for branch,rows in branches.items():
        seen=set()
        for row in rows:
            code=row['code']
            if code in seen: continue
            seen.add(code)
            value=scores.setdefault(code,dict(code=code,name=row['name'],score=0.0,matched_by=[]))
            value['score']+=1/(60+len(seen))
            value['matched_by'].append(branch)
    return sorted(scores.values(),key=lambda r:(-r['score'],r['code']))


def search(query, release=None, semantic=True):
    info=release_info(release)
    params=dict(r=str(info['id']),query=query,normalized=normalize(query))
    # Exact identity is deterministic and never depends on a model call.
    codes=re.findall(r'\b\d\.\d{6}\b',query)
    with engine().connect() as db:
        if codes:
            exact=[dict(r) for r in db.execute(text('''SELECT DISTINCT m.code,m.name FROM rag_item i '''+SCOPE+'''
                WHERE i.release_id=:r AND m.code=ANY(:codes) ORDER BY m.code'''),dict(**params,codes=codes)).mappings()]
            return dict(status='found' if exact else 'not_found',release_id=params['r'],results=fuse({'exact':exact}),degraded=False)
        words=terms(query)
        keyword=[]
        if words:
            params['tsquery']=' | '.join(words)
            keyword=[dict(r) for r in db.execute(text('''SELECT i.code,m.name,i.body,
                ts_rank_cd(i.tsv,to_tsquery('simple',:tsquery)) AS rank FROM rag_item i '''+SCOPE+'''
                WHERE i.release_id=:r AND i.kind='routing' AND i.tsv @@ to_tsquery('simple',:tsquery)
                ORDER BY rank DESC,i.id LIMIT 100'''),params).mappings()]
            keyword=[r for r in keyword if len(set(words)&set(terms(r['body'])))/len(words)>=0.6]
        # pg_trgm's indexable operator supplies bounded typo candidates.
        typo=[dict(r) for r in db.execute(text('''SELECT i.code,m.name,similarity(i.normalized,:normalized) AS rank
            FROM rag_item i '''+SCOPE+''' WHERE i.release_id=:r AND i.kind='routing'
            AND i.normalized % :normalized ORDER BY rank DESC,i.id LIMIT 50'''),params).mappings()]
    branches={'keyword':keyword,'typo':[r for r in typo if r['rank']>=0.45]}
    degraded=False
    if semantic and info['min_similarity'] is not None:
        try:
            vector=embed([query],info['configuration'])[0]  # No database connection held.
            with engine().connect() as db:
                db.execute(text("SET LOCAL hnsw.iterative_scan='strict_order'"))
                rows=[dict(r) for r in db.execute(text('''SELECT i.code,m.name,
                    1-(i.embedding <=> CAST(:v AS vector)) AS similarity FROM rag_item i '''+SCOPE+'''
                    WHERE i.release_id=:r AND i.kind='routing' AND i.embedding IS NOT NULL
                    ORDER BY i.embedding <=> CAST(:v AS vector) LIMIT 100'''),dict(**params,v=vector)).mappings()]
                branches['semantic']=[r for r in rows if r['similarity']>=info['min_similarity']]
        except (httpx.HTTPError,ValueError,KeyError,RuntimeError):
            degraded=True
    results=fuse(branches)[:5]
    return dict(status='found' if results else 'unavailable' if degraded else 'not_found',
                release_id=params['r'],results=results,degraded=degraded)


def members(release,codes):
    with engine().connect() as db:
        return [dict(r) for r in db.execute(text('''SELECT m.* FROM rag_member m
            JOIN procedure p ON p.code=m.code AND p.active AND p.current_snapshot_id=m.snapshot_id
            JOIN procedure_profile_head h ON h.snapshot_id=m.snapshot_id AND h.profile_id=m.profile_id
            WHERE m.release_id=:r AND m.code=ANY(:codes) ORDER BY m.code'''),dict(r=release,codes=codes)).mappings()]


def choice_label(value):
    return {'extend':'Extend an existing permission','issue':'Apply for a new document','cap tinh':'Provincial-level authority',
            'trung uong':'Central-level authority'}.get(normalize(value),value)


def related_codes(release, code):
    """Keep procedures sharing a sourced form as possibilities, never as equivalents.

    A vector threshold can leave just one near-identical procedure above the cut.
    That is not evidence that the user specified its authority or action.
    """
    with engine().connect() as db:
        return list(db.execute(text('''SELECT DISTINCT m.code FROM rag_member m
            JOIN procedure p ON p.code=m.code AND p.active AND p.current_snapshot_id=m.snapshot_id
            JOIN procedure_profile_head h ON h.snapshot_id=m.snapshot_id AND h.profile_id=m.profile_id
            WHERE m.release_id=:r AND (m.code=:code OR EXISTS (
                SELECT 1 FROM rag_member seed,
                jsonb_array_elements(seed.profile->'form_relationships') sf,
                jsonb_array_elements(m.profile->'form_relationships') mf
                WHERE seed.release_id=:r AND seed.code=:code
                AND sf->'form_code'->>'status'='supported'
                AND mf->'form_code'->>'status'='supported'
                AND sf->'form_code'->>'value'=mf->'form_code'->>'value'))
            ORDER BY m.code LIMIT 20'''),dict(r=release,code=code)).scalars())


def match_choice(answer,choices, *, initial=False):
    exact=next((c for c in choices if answer==c['id'] or normalize(answer)==normalize(c['label'])),None)
    if exact:return exact
    value=normalize(answer)
    # Mentioning an option while asking about it is not selecting that option.
    if re.search(r'\b(difference|compare|versus|khac|giai thich)\b',value) or (not initial and
        ('?' in answer or re.search(r'\b(explain|what|why|how|la gi)\b',value))):
        return None
    if value in ("i don't know",'not sure','khong biet','toi khong biet','toi chua ro','chua ro'):
        return next((c for c in choices if c['id']=='unknown'),None)
    if re.search(r"\b(not|no|khong)\b|n't",value):return None
    aliases={'extend my stay':['extend','extension','stay in vietnam longer','stay longer','o lai viet nam lau hon','gia han'],
             'apply for a visa':['issue','issuance','cap thi thuc'],
             'provincial immigration office':['provincial','province','cap tinh'],
             'central immigration department':['central','trung uong']}
    aliases.update({'extend an existing permission':aliases['extend my stay'],
        'apply for a new document':aliases['apply for a visa'],
        'provincial-level authority':aliases['provincial immigration office'],
        'central-level authority':aliases['central immigration department']})
    hits=[c for c in choices if any(re.search(r'\b'+re.escape(term)+r'\b',value)
          for term in aliases.get(normalize(c['label']),[]))]
    return hits[0] if len(hits)==1 else None


def question(candidates,asked):
    # These describe the user's intended action/office, not inferred eligibility.
    # Draft eligibility predicates are deliberately not used as exclusion rules.
    for key,prompt in [('action_type','What do you want to do?'),('authority_level','Which processing level do you need?')]:
        if key in asked: continue
        groups={}
        unknown=[]
        for member in candidates:
            facts=member['profile'].get(key,[])
            if isinstance(facts,dict): facts=[facts]
            supported=[f['value'] for f in facts if f['status']=='supported' and f['value']]
            if not supported: unknown.append(member['code'])
            for value in supported: groups.setdefault(value,[]).append(member['code'])
        if len(groups)<2: continue
        choices=[]
        for index,(label,codes) in enumerate(sorted(groups.items())):
            choices.append(dict(id=str(index),label=choice_label(label),codes=sorted(set(codes+unknown))))
        choices.append(dict(id='unknown',label="I'm not sure",codes=[m['code'] for m in candidates]))
        return dict(key=key,text=prompt,choices=choices)
    return dict(key='procedure',text='Which procedure do you mean?',choices=[
        dict(id=m['code'],label=m['name'],codes=[m['code']]) for m in candidates])


@lru_cache(maxsize=1)
def state_key():
    return os.getenv('RAG_STATE_SECRET','').encode() or secrets.token_bytes(32)


def sign_state(value):
    raw=json.dumps({**value,'expires':int(time.time())+1800},ensure_ascii=False,separators=(',',':')).encode()
    payload=base64.urlsafe_b64encode(raw).decode()
    signature=hmac.new(state_key(),payload.encode(),hashlib.sha256).hexdigest()
    return payload+'.'+signature


class ConversationStateError(ValueError):
    pass


class EvidenceUnavailableError(RuntimeError):
    """Selection is valid, but source verification does not permit factual answers."""


def read_state(token):
    try:
        payload,signature=token.rsplit('.',1)
        if not hmac.compare_digest(signature,hmac.new(state_key(),payload.encode(),hashlib.sha256).hexdigest()): raise ValueError()
        value=json.loads(base64.urlsafe_b64decode(payload))
        if value['expires']<time.time(): raise ValueError()
        return value
    except (ValueError,KeyError,TypeError):
        raise ConversationStateError('This conversation has expired. Start a new conversation to select a procedure again.') from None


def grouped_sources(rows):
    groups={}
    def order(row):
        locator=row['locator']
        match=re.match(r'(section|page):(\d+)',locator)
        return (row['url'],0 if locator=='identity' else 1,int(match[2]) if match else 0,locator)
    for row in sorted(rows,key=order):
        group=groups.setdefault(row['url'],dict(id=row['id'],title=row['title'],url=row['url'],text=''))
        group['text']+=row['locator']+'\n'+row['body']+'\n\n'
    return list(groups.values())


def evidence(release,code,query):
    """Small primary procedures remain complete; extra evidence expands to parents."""
    with engine().connect() as db:
        ready=db.execute(text('''SELECT a.facts_ready,a.evidence_status,a.run_id,m.profile_id FROM rag_member m
            JOIN procedure p ON p.code=m.code AND p.active AND p.current_snapshot_id=m.snapshot_id
            JOIN procedure_profile_head h ON h.snapshot_id=m.snapshot_id AND h.profile_id=m.profile_id
            JOIN procedure_analysis a ON a.snapshot_id=m.snapshot_id
            WHERE m.release_id=:r AND m.code=:c'''),dict(r=release,c=code)).mappings().first()
        from api.evidence_policy import allowed
        if not ready: raise RuntimeError('Retrieval release is stale')
        if not allowed(ready['facts_ready'],ready['evidence_status'],ready['run_id'],ready['profile_id']):
            raise EvidenceUnavailableError('Procedure source details are not yet verified')
        # Row records give the extractor precise coverage anchors. Their text is
        # already present in the complete primary sections; including both here
        # duplicates the evidence and can exhaust the assistant's source budget.
        rows=[dict(r) for r in db.execute(text('''SELECT id,kind,title,url,locator,body FROM rag_source
            WHERE release_id=:r AND code=:c
            AND NOT (kind='procedure' AND (locator LIKE 'requirement:%' OR locator LIKE 'method:%'))
            ORDER BY id'''),dict(r=release,c=code)).mappings()]
    if ready['evidence_status']:
        # Include all competing evidence for reviewed small procedures. Group by
        # original URL, preserving every locator and avoiding top-k conflict loss.
        sources=grouped_sources(rows)
        if len(sources)>20 or sum(len(s['text']) for s in sources)>80000:
            raise RuntimeError('Reviewed evidence exceeds context budget')
        if sources:sources[0]['evidence_status']=ready['evidence_status']
        return sources
    # Rank evidence within the selected procedure, then expand to parent sections.
    # Current, short primary procedures always remain complete.
    vector_scores={}
    try:
        info=release_info(release)
        vector=embed([query],info['configuration'])[0]
        with engine().connect() as db:
            hits=db.execute(text('''SELECT source_id,max(1-(embedding <=> CAST(:v AS vector))) AS score
                FROM rag_item WHERE release_id=:r AND code=:c AND kind='evidence'
                AND embedding IS NOT NULL GROUP BY source_id'''),dict(v=vector,r=release,c=code)).mappings()
            vector_scores={r['source_id']:r['score'] for r in hits}
    except (httpx.HTTPError,ValueError,KeyError,RuntimeError):
        pass  # Complete primary evidence remains available during model outages.
    # Parent text is original evidence, never the profile/extraction registry.
    primary=[r for r in rows if r['kind']=='procedure']
    words=set(terms(query))
    extra=[r for r in rows if r['kind']!='procedure']
    extra.sort(key=lambda r:(-vector_scores.get(r['id'],0),-len(words & set(terms(r['body']))),r['id']))
    chosen=primary+ [r for r in extra if r['id'] in vector_scores or words & set(terms(r['body']))][:min(5,max(0,20-len(primary)))]
    sources=grouped_sources(chosen)
    if len(sources)>20 or sum(len(s['text']) for s in sources)>80000:
        raise RuntimeError('Evidence exceeds context budget; narrow the request')
    return sources


def retrieve(request):
    state=read_state(request.retrieval_state) if request.retrieval_state else None
    resolved_question=request.message
    if request.procedure_code:
        info=release_info()
        state=dict(release=str(info['id']),codes=[request.procedure_code],asked=[],query=request.message)
    elif state is None:
        result=search(request.message)
        if result['status']=='unavailable': raise RuntimeError('Embedding provider unavailable')
        if not result['results']: return dict(sources=[])
        state=dict(release=result['release_id'],codes=[m['code'] for m in result['results']],asked=[],query=request.message)
        if len(state['codes'])==1 and 'exact' not in result['results'][0].get('matched_by',[]):
            state['codes']=related_codes(state['release'],state['codes'][0])
            candidates=members(state['release'],state['codes'])
            # Avoid asking again when the user's words already name an action/office.
            while len(candidates)>1:
                q=question(candidates,state['asked'])
                if q['key']=='procedure':break
                selected=match_choice(request.message,q['choices'],initial=True)
                if not selected or selected['id']=='unknown':break
                state['codes']=selected['codes']
                state['asked'].append(q['key'])
                candidates=[m for m in candidates if m['code'] in state['codes']]
    elif state.get('question'):
        answer=request.clarification_answer or request.message
        q=state['question']
        selected=match_choice(answer,q['choices'])
        if selected:
            resolved_question=state['query']
            state['codes']=selected['codes']
            state['asked'].append(q['key'])
            state.pop('question')
        else:
            return clarification(state)
    current=members(state['release'],state['codes'])
    if len(current)!=len(state['codes']): raise RuntimeError('Procedure changed; restart selection using the current index')
    if len(current)>1:
        state['question']=question(current,state['asked'])
        return clarification(state)
    if not current: return dict(sources=[])
    code=current[0]['code']
    try:
        sources=evidence(state['release'],code,resolved_question)
    except EvidenceUnavailableError:
        return dict(sources=[],procedure_code=code,retrieval_state=sign_state(state),
                    context_notice='This procedure is identified, but its source details are not verified. Only general guidance is available.')
    return dict(sources=sources,procedure_code=code,
                resolved_question=resolved_question,retrieval_state=sign_state(state),profile=current[0].get('profile',{}))


def clarification(state):
    q=state['question']
    current=members(state['release'],state['codes'])
    if len(current)!=len(state['codes']):
        raise RuntimeError('Procedure changed; restart selection using the current index')
    # Selection stays server-owned, but the assistant needs evidence to explain
    # the options. Keep each candidate separate; never merge their requirements.
    sources=[]
    candidates=[]
    budget=80000
    for member in current:
        candidate=dict(code=member['code'],name=member['name'],source_ids=[],evidence_available=False,profile=member.get('profile',{}))
        if len(current)<=5:
            try:
                captured=evidence(state['release'],member['code'],state['query'])
            except RuntimeError:
                captured=[]  # Unreviewed facts are not smuggled in through routing.
            if len(sources)+len(captured)<=20 and sum(len(s['text']) for s in captured)<=budget:
                for index,source in enumerate(captured):
                    source={**source,'id':f"p{member['code'].replace('.','')}_{index}",
                            'title':member['code']+' — '+source['title']}
                    sources.append(source)
                    candidate['source_ids'].append(source['id'])
                    budget-=len(source['text'])
                candidate['evidence_available']=bool(captured)
        candidates.append(candidate)
    return dict(clarification=q['text'],choices=[dict(id=c['id'],label=c['label']) for c in q['choices']],
                retrieval_state=sign_state(state),sources=sources,candidates=candidates,
                original_question=state['query'])
