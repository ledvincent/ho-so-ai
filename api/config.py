import os
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def coverage():
    selected = yaml.safe_load((ROOT / "candidates.yaml").read_text(encoding="utf-8"))
    return dict(source_base='https://vpcp.dichvucong.gov.vn/p/home/dvc-chi-tiet-thu-tuc-nganh-doc.html',
                procedures=[dict(code=p['code'],expected_name=p.get('expected_name',p['name']),audience='foreigner') for p in selected['procedures']])


@lru_cache(maxsize=1)
def engine():
    return create_engine(os.getenv("DATABASE_URL", "postgresql+psycopg://hoso:hoso_local@localhost:55432/hoso"),
                         connect_args={"connect_timeout": 5}, pool_pre_ping=True)
