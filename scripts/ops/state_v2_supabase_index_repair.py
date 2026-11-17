#!/usr/bin/env python3
"""Run the bounded State v2 Supabase index repair in autocommit mode.

This script repairs only the project_id and job_id expression indexes on
public.research_proactive_memory. It does not alter migration history or start
any application or Research runtime.
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg


HOST = "aws-1-us-west-2.pooler.supabase.com"
PORT = 5432
DATABASE = "postgres"
USER = "postgres.iqjwgpnujbeoyaeuwehj"
TABLE = "public.research_proactive_memory"
PROJECT_INDEX = "research_proactive_memory_project_id_idx"
JOB_INDEX = "research_proactive_memory_job_id_idx"
RUNTIME_ENV = Path.home() / ".config/nexus/runtime.env"


def _password_from_runtime_env(path: Path) -> str | None:
    """Read only PGPASSWORD from the approved runtime environment file."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return None

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export "):].lstrip()
        key, separator, value = stripped.partition("=")
        if separator and key.strip() == "PGPASSWORD":
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            return value or None
    return None


def _password() -> str:
    value = os.environ.get("PGPASSWORD")
    if value:
        return value
    value = _password_from_runtime_env(RUNTIME_ENV)
    if value:
        return value
    raise RuntimeError("PGPASSWORD is unavailable in the approved sources")


def _index_state(cursor: psycopg.Cursor, index_name: str) -> tuple[bool, bool] | None:
    cursor.execute(
        """SELECT i.indisvalid, i.indisready
             FROM pg_catalog.pg_index AS i
             JOIN pg_catalog.pg_class AS idx ON idx.oid = i.indexrelid
             JOIN pg_catalog.pg_namespace AS ns ON ns.oid = idx.relnamespace
            WHERE ns.nspname = 'public' AND idx.relname = %s""",
        (index_name,),
    )
    row = cursor.fetchone()
    return (bool(row[0]), bool(row[1])) if row else None


def _assert_state(cursor: psycopg.Cursor, index_name: str, expected: tuple[bool, bool]) -> None:
    actual = _index_state(cursor, index_name)
    if actual != expected:
        raise RuntimeError(f"Unexpected catalog state for {index_name}: {actual!r}")


def _assert_no_active_build(cursor: psycopg.Cursor) -> None:
    cursor.execute(
        """SELECT EXISTS (
               SELECT 1
                 FROM pg_catalog.pg_stat_progress_create_index AS p
                 JOIN pg_catalog.pg_class AS t ON t.oid = p.relid
                 JOIN pg_catalog.pg_namespace AS n ON n.oid = t.relnamespace
                WHERE n.nspname = 'public' AND t.relname = 'research_proactive_memory'
           )"""
    )
    if cursor.fetchone()[0]:
        raise RuntimeError("An index build is already active for the target table")


def main() -> None:
    # Confirm the expected psycopg 3.3.6 binary implementation before connecting.
    if psycopg.__version__ != "3.3.6" or psycopg.pq.__impl__ != "binary":
        raise RuntimeError("Expected psycopg 3.3.6 with the binary implementation")

    with psycopg.connect(
        host=HOST,
        port=PORT,
        dbname=DATABASE,
        user=USER,
        password=_password(),
        sslmode="require",
        connect_timeout=10,
        autocommit=True,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            if cursor.fetchone() != (1,):
                raise RuntimeError("Supabase connection check failed")

            _assert_state(cursor, PROJECT_INDEX, (False, False))
            if _index_state(cursor, JOB_INDEX) is not None:
                raise RuntimeError("The job_id index is expected to be absent")
            _assert_no_active_build(cursor)

            cursor.execute(f"DROP INDEX CONCURRENTLY public.{PROJECT_INDEX}")
            if _index_state(cursor, PROJECT_INDEX) is not None:
                raise RuntimeError("The invalid project_id index remains present")

            cursor.execute(
                f"""CREATE INDEX CONCURRENTLY {PROJECT_INDEX}
                    ON {TABLE} ((payload ->> 'project_id'))
                    WHERE payload ? 'project_id'"""
            )
            _assert_state(cursor, PROJECT_INDEX, (True, True))

            cursor.execute(
                f"""CREATE INDEX CONCURRENTLY {JOB_INDEX}
                    ON {TABLE} ((payload ->> 'job_id'))
                    WHERE payload ? 'job_id'"""
            )
            _assert_state(cursor, PROJECT_INDEX, (True, True))
            _assert_state(cursor, JOB_INDEX, (True, True))


if __name__ == "__main__":
    main()
