import runpy
from pathlib import Path

import dotenv


def test_disabled_dotenv_never_calls_loader(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Local .env must not be opened")

    monkeypatch.setenv("HOSO_LOAD_DOTENV", "0")
    monkeypatch.setattr(dotenv, "load_dotenv", forbidden)
    runpy.run_path(str(Path(__file__).resolve().parents[1] / "api/config.py"))
