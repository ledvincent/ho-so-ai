"""Corpus routing evaluation. Does not approve sources or automatically enable thresholds."""
import argparse
import json
import time
import re
from pathlib import Path
from sqlalchemy import text
from api.config import ROOT,engine
from api.rag import search
from api.rag_index import embed


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release',required=True)
    parser.add_argument('--output',type=Path,default=ROOT/'output/rag-evaluation.json')
    args=parser.parse_args()
    cases=json.loads((ROOT/'tests/fixtures/rag_queries.json').read_text(encoding='utf-8'))
    with engine().connect() as db:
        config=db.execute(text('SELECT s.configuration FROM embedding_space s JOIN rag_release r ON r.space_id=s.id WHERE r.id=:r'),dict(r=args.release)).scalar_one()
    results=[]
    for case in cases:
        start=time.perf_counter()
        vector=embed([case['query']],config)[0]
        with engine().connect() as db:
            scores=[dict(r) for r in db.execute(text('''SELECT i.code,max(1-(c.embedding <=> CAST(:v AS vector))) AS similarity
                FROM rag_item i JOIN rag_release r ON r.id=i.release_id
                JOIN embedding_cache c ON c.space_id=r.space_id AND c.input_hash=i.input_hash
                WHERE i.release_id=:r AND i.kind='routing' AND c.embedding IS NOT NULL
                GROUP BY i.code ORDER BY similarity DESC'''),dict(v=vector,r=args.release)).mappings()]
        if not scores: raise RuntimeError('Complete the embedding queue before evaluation')
        lexical=[r['code'] for r in search(case['query'],release=args.release,semantic=False)['results']]
        results.append(dict(**case,scores=scores,lexical_candidates=lexical,seconds=time.perf_counter()-start))
    calibration=[r for r in results if r['split']=='calibration']
    negatives=max(r['scores'][0]['similarity'] for r in calibration if not r['codes'])
    # Calibrate the union of lexical and vector retrieval. Accentless inputs may
    # correctly rely on lexical retrieval despite low multilingual cosine scores.
    positive_scores=[max(s['similarity'] for s in r['scores'] if s['code'] in r['codes']) for r in calibration if r['codes']]
    semantic_only=[max(s['similarity'] for s in r['scores'] if s['code'] in r['codes'])
                   for r in calibration if r['codes'] and not set(r['codes'])&set(r['lexical_candidates'])]
    upper=min(semantic_only) if semantic_only else min((s for s in positive_scores if s>negatives),default=negatives)
    proposed=(negatives+upper)/2 if negatives<upper else None
    for r in results:
        predicted=[s['code'] for s in r['scores'] if proposed is not None and s['similarity']>=proposed]
        exact=re.findall(r'\b\d\.\d{6}\b',r['query'])
        if exact: predicted=[s['code'] for s in r['scores'] if s['code'] in exact]
        r['semantic_candidates']=predicted
        combined=set(predicted)|set(r['lexical_candidates'])
        r['combined_candidates']=sorted(combined)
        r['candidate_check']=bool(combined&set(r['codes'])) if r['codes'] else not combined
    report=dict(release=args.release,model=config,proposed_min_similarity=proposed,results=results,
                calibration_passed=all(r['candidate_check'] for r in results if r['split']=='calibration'),
                note='Small development benchmark; labels and semantic quality need review. No readiness or configuration changes made.')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(proposed_min_similarity=proposed,test_passed=sum(r['candidate_check'] for r in results if r['split']=='test'),test_total=sum(r['split']=='test' for r in results),report=str(args.output))))


if __name__=='__main__': main()
