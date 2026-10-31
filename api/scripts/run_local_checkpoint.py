"""Explicit loopback launcher. Load an existing key in memory; never copy/log it."""

import argparse
import os
from pathlib import Path
import sys

from dotenv import dotenv_values
import uvicorn


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--origin", default="http://127.0.0.1:3016")
    parser.add_argument("--port", type=int, default=8016)
    parser.add_argument("--key-file", type=Path)
    parser.add_argument("--demo-seed", action="store_true")
    args = parser.parse_args()
    if not args.database.is_absolute() or not 1024 <= args.port <= 65535:
        parser.error("An absolute database path and local user port are required.")
    if args.key_file:
        if not args.key_file.is_file() or args.key_file.is_symlink():
            parser.error("The authorized credential file is unavailable.")
        # Only this variable is consumed. Never write the dotenv values anywhere.
        key = dotenv_values(args.key_file).get("OPENAI_API_KEY")
        if not key:
            parser.error("OPENAI_API_KEY is absent from the authorized file.")
        os.environ["OPENAI_API_KEY"] = key
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from hoso_api.main import create_app
    from hoso_api.settings import Settings
    config = Settings(
        auth_provider="local", public_origin=args.origin,
        local_api_host="127.0.0.1", local_db_path=str(args.database),
        local_demo_seed=args.demo_seed, demo_forms_enabled=True,
        cors_allowed_origins=(args.origin,),
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
        assistant_model=os.environ.get("ASSISTANT_MODEL", "gpt-4o-mini"),
    )
    uvicorn.run(create_app(config), host="127.0.0.1", port=args.port,
                access_log=False, proxy_headers=False, log_level="warning")


if __name__ == "__main__":
    main()
