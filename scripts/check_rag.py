"""PostgreSQL integration checks in a rolled-back transaction; no model calls."""
from contextlib import contextmanager
from unittest.mock import patch
import httpx
from sqlalchemy import text
from api.config import engine
from api import rag,rag_index


def main():
    with engine().connect() as db:
        tx=db.begin()
        class Bound:
            @contextmanager
            def connect(self): yield db
            @contextmanager
            def begin(self):
                with db.begin_nested(): yield db
        bound=Bound()
        vector='['+','.join(['1']+['0']*1023)+']'
        try:
            before=list(db.execute(text('SELECT snapshot_id,facts_ready FROM procedure_analysis ORDER BY snapshot_id')))
            with patch.object(rag_index,'engine',lambda:bound),patch.object(rag,'engine',lambda:bound),\
                 patch.object(rag_index,'embed',lambda values,c:[vector]*len(values)),\
                 patch.object(rag,'embed',lambda values,c:[vector]*len(values)):
                release=rag_index.build(dict(model='fixture',revision='fixture',dimensions=1024))
                assert rag_index.build(dict(model='fixture',revision='fixture',dimensions=1024))==release
                try: rag_index.publish(release)
                except RuntimeError: pass
                else: raise AssertionError('Incomplete release was published')
                assert rag_index.work(release)>0
                assert rag_index.work(release)==0
                rag_index.publish(release,0.6)
                found=rag.search('1.001146')
                assert [r['code'] for r in found['results']]==['1.001146']
                assert rag.search('9.999999')['results']==[]
                assert rag.search('gia han tam tru',semantic=False)['results']
                assert rag.search('qzxwvplm',semantic=False)['results']==[]
                assert rag.search('register a company',semantic=False)['results']==[]
                with patch.object(rag,'embed',side_effect=httpx.ConnectError('offline')):
                    fallback=rag.search('gia han tam tru')
                    assert fallback['degraded'] and fallback['results']
                    assert rag.search('qzxwvplm')['status']=='unavailable'
                    assert rag.search('1.001146')['degraded'] is False
                # Unknown readiness blocks must survive successful indexing.
                db.execute(text("UPDATE procedure_analysis SET evidence_status='{}'::jsonb"))
                try: rag.evidence(release,'1.001146','documents')
                except RuntimeError: pass
                else: raise AssertionError('Blocked evidence escaped')
                assert list(db.execute(text('SELECT snapshot_id,facts_ready FROM procedure_analysis ORDER BY snapshot_id')))==before
                # A rollback-only fixture exercises compact approved evidence.
                db.execute(text('UPDATE procedure_analysis SET facts_ready=true WHERE snapshot_id IN (SELECT current_snapshot_id FROM procedure WHERE active)'))
                for code in db.execute(text('SELECT code FROM procedure WHERE active')).scalars():
                    sources=rag.evidence(release,code,'documents fees forms')
                    assert len(sources)<=20 and sum(len(s['text']) for s in sources)<80000
                    primary=db.execute(text("SELECT id FROM rag_source WHERE release_id=:r AND code=:c AND kind='procedure'"),dict(r=release,c=code)).scalars().all()
                    assert set(primary)<=set(s['id'] for s in sources)
                    assert all(s['url'].startswith('https://') for s in sources)
                # Stale membership cannot serve after a profile switch/removal.
                db.execute(text('UPDATE procedure SET active=false WHERE code=\'1.001146\''))
                assert rag.search('1.001146')['results']==[]
                try: rag.evidence(release,'1.001146','help')
                except RuntimeError: pass
                else: raise AssertionError('Inactive evidence escaped')
            print('PASS: release idempotency, pending publication, cached embeddings, SQL routing, readiness gates, compact evidence, stale membership; all fixture changes rolled back.')
        finally: tx.rollback()


if __name__=='__main__': main()
