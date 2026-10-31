import argparse
import hashlib
import json
import httpx

from sqlalchemy import text

from api.config import ROOT, coverage, engine
from api.db import ingest
from api.fetch import Fetcher, fetch_pages
from api.parse import parse


def parse_pages(load=False):
    manifest_path = ROOT/'data/_store/manifest.json'
    if not manifest_path.exists():
        manifest_path = ROOT/'data/archive/raw/manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output = ROOT / "data/_store/parsed"
    output.mkdir(parents=True, exist_ok=True)
    for entry in coverage()["procedures"]:
        code = entry["code"]
        source = manifest[code]
        raw = (ROOT / source["raw_path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != source["sha256"]:
            raise ValueError(f"Snapshot hash mismatch for {code}")
        parsed = parse(raw, code, source["url"], source["fetched_at"], entry["expected_name"])
        (output / f"{code}.json").write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
        if load:
            ingest(parsed, entry["audience"], source["raw_path"])
        print(f"{code}: {parsed['name']} | {len(parsed['requirements'])} requirements | {len(parsed['fees'])} fees | {parsed['status']}")


def fetch_forms():
    fetcher = Fetcher()
    with engine().connect() as db:
        rows = list(db.execute(text("""SELECT DISTINCT pf.source_url FROM procedure_form pf
            JOIN procedure p ON p.current_snapshot_id=pf.snapshot_id""")).scalars())
    for url in rows:
        try:
            record = fetcher.get(url, "forms")
            with engine().begin() as db:
                db.execute(text("INSERT INTO form(sha256,raw_path) VALUES (:sha256,:raw_path) ON CONFLICT DO NOTHING"), record)
                db.execute(text("""UPDATE procedure_form SET form_sha256=:sha256,fetched_at=:fetched_at
                    WHERE source_url=:url AND snapshot_id IN (SELECT current_snapshot_id FROM procedure)"""), record)
            print(f"saved {record['sha256']}")
        except (ValueError, httpx.HTTPError) as exc:
            print(f"FAILED {url}: {exc}")
            raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["fetch", "parse", "ingest", "fetch-forms", "embed"])
    command = parser.parse_args().command
    if command == "fetch":
        fetch_pages()
    elif command in ("parse", "ingest"):
        parse_pages(load=command == "ingest")
    elif command == "fetch-forms":
        fetch_forms()
    else:
        from api.search import embed_pending
        embed_pending()


if __name__ == "__main__":
    main()
