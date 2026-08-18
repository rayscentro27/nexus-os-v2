"""Read-only Supabase REST adapter shared by governed Nexus capabilities.

The repository historically returned ``requests.Session`` from one helper and
then treated it as a Supabase Python client elsewhere.  This adapter gives
the governed read layer one explicit contract while retaining the small
``table().select().execute()`` surface used by existing handlers.

It intentionally exposes no mutation methods and only permits approved read
tables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional


APPROVED_READ_TABLES = frozenset({
    "client_profiles",
    "nexus_process_definitions",
    "nexus_process_runs",
    "nexus_research_runs",
    "nexus_research_results",
    "business_opportunities",
})


@dataclass
class ReadResponse:
    """Small response compatible with the fields used by Nexus readers."""

    data: Any
    status_code: int = 200
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300


class _ReadQuery:
    def __init__(self, client: "GovernedSupabaseReadClient", table: str):
        self.client = client
        self.table_name = table
        self.params: Dict[str, Any] = {"select": "*"}

    def select(self, columns: str = "*") -> "_ReadQuery":
        self.params["select"] = columns
        return self

    def order(self, column: str, desc: bool = False) -> "_ReadQuery":
        self.params["order"] = f"{column}.{'desc' if desc else 'asc'}"
        return self

    def limit(self, value: int) -> "_ReadQuery":
        self.params["limit"] = max(0, min(int(value), 1000))
        return self

    def eq(self, column: str, value: Any) -> "_ReadQuery":
        self.params[column] = f"eq.{value}"
        return self

    def in_(self, column: str, values: Iterable[Any]) -> "_ReadQuery":
        self.params[column] = "in.(" + ",".join(str(v) for v in values) + ")"
        return self

    def gte(self, column: str, value: Any) -> "_ReadQuery":
        self.params[column] = f"gte.{value}"
        return self

    def execute(self) -> ReadResponse:
        return self.client._get_table(self.table_name, self.params)


class GovernedSupabaseReadClient:
    """Explicit read-only client used by Hermes and Nova's shared layer."""

    def __init__(self, url: str, key: str, session: Any = None):
        import requests

        self._supabase_url = url.rstrip("/")
        self._session = session or requests.Session()
        self._session.headers.update({
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Prefer": "count=exact",
        })

    def table(self, table: str) -> _ReadQuery:
        if table not in APPROVED_READ_TABLES:
            raise ValueError(f"Table is not approved for governed reads: {table}")
        return _ReadQuery(self, table)

    def get(self, url: str, **kwargs: Any) -> Any:
        """Compatibility path for existing exact, approved REST reads."""
        return self._session.get(url, **kwargs)

    def _get_table(self, table: str, params: Dict[str, Any]) -> ReadResponse:
        try:
            response = self._session.get(
                f"{self._supabase_url}/rest/v1/{table}",
                params=params,
                timeout=10,
            )
            try:
                data = response.json()
            except Exception:
                data = []
            return ReadResponse(data=data, status_code=response.status_code)
        except Exception as exc:
            return ReadResponse(data=[], status_code=599, error=str(exc))


def create_supabase_read_client() -> Optional[GovernedSupabaseReadClient]:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return None
    try:
        return GovernedSupabaseReadClient(url, key)
    except Exception:
        return None
