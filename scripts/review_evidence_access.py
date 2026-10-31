"""Record a scoped access review for the four captured profiles; never approve forms."""
import json
from datetime import datetime,timezone
from sqlalchemy import text
from api.config import engine,ROOT
from api.evidence_policy import VERSION
from api.profiles import walk

def main():
    reviews=[]
    with engine().begin() as db:
        rows=db.execute(text("""SELECT p.code,s.status,s.document_json,a.snapshot_id,a.run_id,a.facts_ready,r.report,
            pp.id AS profile_id,pp.profile FROM procedure p JOIN source_page s ON s.id=p.current_snapshot_id
            JOIN procedure_analysis a ON a.snapshot_id=s.id JOIN analysis_run r ON r.id=a.run_id
            JOIN procedure_profile_head h ON h.snapshot_id=s.id JOIN procedure_profile pp ON pp.id=h.profile_id
            WHERE p.active ORDER BY p.code""")).mappings().all()
        assert {r['code'] for r in rows}=={'1.003326','1.001146','1.003342','1.000771'}
        for r in rows:
            assert r['status']=='parsed' and r['document_json'] and r['profile']
            assert r['report'].get('freshness',{}).get('status')=='requires_recheck'
            assert not any('expired applicability' in i.lower() for i in r['report'].get('issues',[]))
            conflicts=[n for n in walk(r['profile']) if n.get('status')=='conflict' and 'source_refs' in n]
            review=dict(policy=VERSION,access='source_attributed',run_id=str(r['run_id']),profile_id=r['profile_id'],
                reviewed_at=datetime.now(timezone.utc).isoformat(),procedure_currency='not_reverified',
                form_applicability='unresolved',template_approval='unchanged',conflicting_claims=conflicts,
                reason='The legacy form-revision mismatch alone does not invalidate all captured procedure facts.',
                official_checks=[dict(url='https://congbao.chinhphu.vn/van-ban/thong-tu-so-70-2026-tt-bca-469801.htm',finding='Gazette records issue 2026-05-25 and effect 2026-07-01; this does not verify every procedure claim.'),
                dict(url='https://congan.cantho.gov.vn/thu-tuc-hanh-chinh/thutuc/gia-han-tam-tru-cho-nguoi-nuoc-ngoai-tai-viet-nam-3.html',finding='Provincial page explicitly names NA5 under 70/2026/TT-BCA; applicability is not generalized to all four procedures.')])
            db.execute(text('UPDATE procedure_analysis SET evidence_status=CAST(:review AS jsonb) WHERE snapshot_id=:sid'),dict(review=json.dumps(review),sid=r['snapshot_id']))
            reviews.append(dict(code=r['code'],snapshot_id=r['snapshot_id'],**review))
    folder=ROOT/'data/reviews';folder.mkdir(exist_ok=True)
    path=folder/('evidence-access-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json')
    path.write_text(json.dumps(reviews,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Scoped reviews recorded:',len(reviews),path)
if __name__=='__main__':main()
