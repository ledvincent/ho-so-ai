"""Start the restored upstream API with an interactive process-only key."""
import argparse
import getpass
import os
from pathlib import Path
import secrets
import sys
import warnings


def install_provider_diagnostics(app):
    """Observe status only in this launcher; leave Vincent's source untouched."""
    import httpx
    original = httpx.post
    observation = {"http_status":None, "code":None}
    allowed = {"invalid_api_key", "model_not_found", "insufficient_quota",
               "rate_limit_exceeded", "unsupported_value", "invalid_request_error",
               "permission_denied", "account_deactivated"}
    def post(url, *args, **kwargs):
        if str(url) != "https://api.openai.com/v1/chat/completions":
            return original(url, *args, **kwargs)
        try:
            response = original(url, *args, **kwargs)
        except httpx.HTTPError:
            observation.update(http_status=None, code="transport_error")
            raise
        code = None
        if response.is_error:
            try:
                candidate = response.json().get("error", {}).get("code")
                code = candidate if candidate in allowed else "provider_error"
            except (ValueError, AttributeError, TypeError):
                code = "provider_error"
        observation.update(http_status=response.status_code, code=code)
        return response
    httpx.post = post

    @app.get("/voice-runtime/diagnostics", include_in_schema=False)
    def diagnostics():
        return {"provider":dict(observation), "runtime_commit":"7c78ec4a731a2200d834f40e530eb0f2b5b9d38e"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-generation", action="store_true", help="Verify restored data without a provider key")
    args = parser.parse_args()
    runtime = Path(__file__).resolve().parents[3] / "work/vincent-runtime-7c78ec4"
    if not (runtime / "api/main.py").is_file():
        raise SystemExit("Pinned upstream runtime missing")
    os.chdir(runtime)
    sys.path.insert(0, str(runtime))
    os.environ.update({"HOSO_LOAD_DOTENV":"0",
        "DATABASE_URL":"postgresql+psycopg://hoso:hoso_local@127.0.0.1:55432/hoso_kim_demo",
        "ASSISTANT_BASE_URL":"https://api.openai.com/v1",
        "ASSISTANT_MODEL":"gpt-6.1-sol", "ASSISTANT_REASONING_EFFORT":"medium",
        "RAG_EMBED_URL":"http://127.0.0.1:11434", "EMBED_MODEL":"bge-m3",
        "RAG_STATE_SECRET":secrets.token_hex(32), "FORM_REVIEW_SECRET":secrets.token_hex(32)})
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("ASSISTANT_API_KEY", None)
    from api.config import engine
    from sqlalchemy import text
    try:
        with engine().connect() as connection:
            count = connection.execute(text("SELECT count(*) FROM procedure WHERE active")).scalar_one()
        if count < 1:
            raise ValueError()
    except Exception:
        raise SystemExit("Restored database unavailable or empty; no key requested") from None
    print(f"Restored database available: {count} active procedures.")
    if not args.no_generation:
        if not sys.stdin.isatty():
            raise SystemExit("Use an interactive terminal for the hidden key prompt.")
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            try:
                key = getpass.getpass("OpenAI API key (hidden, process only): ").strip()
            except (getpass.GetPassWarning, EOFError):
                raise SystemExit("Hidden input unavailable; key was not read.") from None
        if not key or any(c.isspace() for c in key):
            raise SystemExit("Empty or invalid key; nothing saved.")
        os.environ["ASSISTANT_API_KEY"] = key
        del key
    from api.main import app
    install_provider_diagnostics(app)
    import uvicorn
    print("Vincent API: http://127.0.0.1:8004 ; no key or transcript access logs.")
    uvicorn.run(app, host="127.0.0.1", port=8004, access_log=False)


if __name__ == "__main__":
    main()
