"""Archive exploratory files without deleting them; export the active four."""
import json
import shutil
import yaml
from sqlalchemy import text
from api.config import ROOT,engine
from api.storage import export_procedure,write_json

FOLDERS = ('raw','forms','derived','reports','parsed','inbox')

def rewrite(value):
    if isinstance(value,str):
        for folder in FOLDERS:
            if value.startswith('data/'+folder+'/'):
                return value.replace('data/'+folder+'/', 'data/archive/'+folder+'/',1)
        return value
    if isinstance(value,list):
        return [rewrite(v) for v in value]
    if isinstance(value,dict):
        return {k:rewrite(v) for k,v in value.items()}
    return value

def main():
    data = (ROOT/'data').resolve()
    for name in FOLDERS:
        src,dest = (data/name).resolve(),(data/'archive'/name).resolve()
        assert src.is_relative_to(data) and dest.is_relative_to(data) and src!=data
        if src.exists():
            if dest.exists():
                raise RuntimeError(f'Archive already exists: {dest}; no overwrite performed')
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.move(str(src),str(dest))
    for path in (data/'archive').rglob('*.json'):
        write_json(path,rewrite(json.loads(path.read_text(encoding='utf-8'))))
    codes = [p['code'] for p in yaml.safe_load((ROOT/'candidates.yaml').read_text(encoding='utf-8'))['procedures']]
    with engine().begin() as db:
        for table,columns in [('source_page',['raw_path']),('form',['raw_path','pdf_path'])]:
            for row in db.execute(text(f'SELECT * FROM {table}')).mappings().all():
                key = 'id' if table=='source_page' else 'sha256'
                for col in columns:
                    if row[col] and rewrite(row[col])!=row[col]:
                        db.execute(text(f'UPDATE {table} SET {col}=:value WHERE {key}=:key'),dict(value=rewrite(row[col]),key=row[key]))
        for row in db.execute(text('SELECT id,report FROM analysis_run')).mappings().all():
            db.execute(text('UPDATE analysis_run SET report=CAST(:report AS jsonb) WHERE id=:id'),dict(report=json.dumps(rewrite(row['report'])),id=row['id']))
        db.execute(text('UPDATE procedure SET active=false'))
        for code in codes:
            db.execute(text('UPDATE procedure SET active=true WHERE code=:code'),dict(code=code))
    for code in codes:
        export_procedure(code)
    rows = []
    for code in codes:
        p = json.loads((data/'procedures'/code/'procedure.json').read_text(encoding='utf-8'))
        rows.append(f"| [{code}](procedures/{code}/README.md) | {p['name']} | [Word](procedures/{code}/forms/NA5.doc) · [PDF](procedures/{code}/forms/NA5.pdf) · [Fields](procedures/{code}/forms/NA5.fields.json) |")
    (data/'README.md').write_text('# Active procedure data\n\nStart here. Four procedures; two distinct downloaded NA5 files are reused across them. All are drafts pending the issues in each analysis.json.\n\n| Procedure | Official name | Form files |\n| --- | --- | --- |\n'+'\n'.join(rows)+'\n\n`procedures/` is the readable working dataset. `archive/` contains earlier exploration, old candidates and historical versions; it is not the active shortlist. `_store/` holds future internal hash-addressed artifacts. The database stores facts, relationships and field definitions; file paths point to original/derived artifacts.\n\nProcedure 1.002411 was removed from the active set because its form download returns 503. Its history is archived.\n',encoding='utf-8')
    print('Organized four active procedures; archived exploration; updated database paths. No original files deleted.')

if __name__=='__main__':
    main()
