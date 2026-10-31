"""Explicit, offline additive upgrade for a named ISOLATED SQLite test copy.

Never invoked by application startup. Confirmation is an operator attestation;
the tool cannot determine whether another process is using a database.
"""

import argparse
from pathlib import Path
import sqlite3


def upgrade_isolated_database(database: str | Path, *, confirm_isolated: bool = False) -> bool:
    """Return True when added, False when already present; never create a DB."""
    path = Path(database)
    if (
        confirm_isolated is not True or not path.is_absolute() or not path.is_file()
        or path.is_symlink() or any(parent.is_symlink() for parent in path.parents)
    ):
        raise ValueError("Name an existing absolute isolated database and confirm isolation.")
    connection = sqlite3.connect(path.as_uri() + "?mode=rw", uri=True, timeout=1, isolation_level=None)
    try:
        connection.execute("BEGIN IMMEDIATE")
        table = connection.execute(
            "SELECT type FROM sqlite_master WHERE name='profiles'"
        ).fetchone()
        columns = {row[1] for row in connection.execute("PRAGMA table_info(profiles)")}
        required = {
            "owner_subject", "profile_id", "revision", "full_name", "date_of_birth",
            "nationality", "address", "phone_number", "email",
        }
        if table != ("table",) or not required.issubset(columns):
            raise ValueError("The isolated database does not have the expected profile table.")
        changed = "details_json" not in columns
        if changed:
            connection.execute("ALTER TABLE profiles ADD COLUMN details_json TEXT NOT NULL DEFAULT '{}'")
        connection.commit()
        return changed
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, help="Absolute path to an existing isolated SQLite copy.")
    parser.add_argument("--confirm-isolated", action="store_true", help="Attest this is an isolated offline test copy.")
    args = parser.parse_args()
    try:
        changed = upgrade_isolated_database(args.database, confirm_isolated=args.confirm_isolated)
    except (ValueError, OSError, sqlite3.Error):
        parser.exit(2, "Isolated profile upgrade refused or unavailable. No details disclosed.\n")
    print("Isolated profile extension added." if changed else "Isolated profile extension already present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
