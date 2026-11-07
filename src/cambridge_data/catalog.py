"""Search and cache the Socrata catalog for the Cambridge Open Data portal.

The Discovery API (api.us.socrata.com/api/catalog/v1) lists every public
dataset on the portal with rich metadata (columns, tags, category, update
frequency) and needs no auth. refresh_catalog() snapshots it locally as
Parquet so dataset discovery is a fast offline search, not a live call.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import requests

from cambridge_data.config import DISCOVERY_DOMAIN, PORTAL_DOMAIN, cache_dir, load_credentials

DATA_DIR = cache_dir()
CATALOG_PARQUET = DATA_DIR / "catalog.parquet"
_TIMEOUT = 60
_PAGE_SIZE = 100


def _fetch_all_catalog_entries() -> list[dict[str, Any]]:
    """Pull every catalog descriptor for the portal domain from the Discovery API.

    Returns:
        Raw catalog result dicts as returned by the Discovery API.
    """
    creds = load_credentials()
    session = requests.Session()
    session.headers.update(creds.headers)
    if creds.basic_auth:
        session.auth = creds.basic_auth

    entries: list[dict[str, Any]] = []
    offset = 0
    while True:
        response = session.get(
            f"https://{DISCOVERY_DOMAIN}/api/catalog/v1",
            params={"domains": PORTAL_DOMAIN, "limit": _PAGE_SIZE, "offset": offset},
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        entries.extend(results)
        if len(results) < _PAGE_SIZE:
            return entries
        offset += _PAGE_SIZE


def _extract_update_frequency(entry: dict[str, Any]) -> str:
    for item in entry.get("classification", {}).get("domain_metadata", []):
        if item.get("key", "").endswith("Update-Frequency"):
            return item.get("value", "")
    return ""


def refresh_catalog() -> int:
    """Refresh the local catalog cache from the live Discovery API.

    Only "dataset"-type entries are kept (stories, charts, maps, and other
    non-tabular assets are dropped -- they aren't queryable via SODA).

    Returns:
        Number of dataset entries written to data/catalog.parquet.
    """
    entries = _fetch_all_catalog_entries()
    rows = [
        {
            "id": entry["resource"]["id"],
            "name": entry["resource"]["name"],
            "description": entry["resource"].get("description") or "",
            "category": entry.get("classification", {}).get("domain_category") or "",
            "tags": list(entry.get("classification", {}).get("domain_tags") or []),
            "columns_name": list(entry["resource"].get("columns_name") or []),
            "columns_field_name": list(entry["resource"].get("columns_field_name") or []),
            "columns_datatype": list(entry["resource"].get("columns_datatype") or []),
            "update_frequency": _extract_update_frequency(entry),
            "data_updated_at": entry["resource"].get("data_updated_at") or "",
            "page_views_total": entry["resource"].get("page_views", {}).get("page_views_total", 0),
            "link": entry.get("link") or "",
        }
        for entry in entries
        if entry["resource"]["type"] == "dataset"
    ]
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(CATALOG_PARQUET, index=False)
    return len(rows)


_LIST_COLUMNS = ("tags", "columns_name", "columns_field_name", "columns_datatype")


def _plain_row(row: dict[str, Any]) -> dict[str, Any]:
    """Coerce list-typed catalog columns to plain Python lists.

    pandas returns list-valued columns (tags, field names, datatypes) as numpy
    arrays, which are not JSON-serializable. Callers that return catalog rows to
    a JSON consumer (the MCP server, an API) need plain lists.

    Args:
        row: A catalog row as returned by ``to_dict``.

    Returns:
        The same row with list columns coerced to ``list[str]``.
    """
    for column in _LIST_COLUMNS:
        value = row.get(column)
        if value is not None:
            row[column] = [str(item) for item in list(value)]
    return row


def search(keyword: str, *, limit: int = 20) -> list[dict[str, Any]]:
    """Search the cached catalog for datasets matching a keyword.

    Matches (case-insensitive substring) against name, description,
    category, and tags.

    Args:
        keyword: Free-text search term.
        limit: Maximum number of results to return.

    Returns:
        Matching catalog rows, most page-viewed first.

    Raises:
        FileNotFoundError: If the catalog cache has never been refreshed.
    """
    if not CATALOG_PARQUET.exists():
        raise FileNotFoundError(
            f"No catalog cache at {CATALOG_PARQUET}. Run scripts/refresh_catalog.py first."
        )
    df = pd.read_parquet(CATALOG_PARQUET)
    kw = keyword.lower()
    tags_match = df["tags"].apply(lambda tags: any(kw in tag.lower() for tag in tags))
    mask = (
        df["name"].str.lower().str.contains(kw, regex=False)
        | df["description"].str.lower().str.contains(kw, regex=False)
        | df["category"].str.lower().str.contains(kw, regex=False)
        | tags_match
    )
    matches = df[mask].sort_values("page_views_total", ascending=False).head(limit)
    return [_plain_row(row) for row in matches.to_dict(orient="records")]


def get(dataset_id: str) -> dict[str, Any] | None:
    """Look up a single cached catalog entry by dataset id.

    Args:
        dataset_id: Socrata four-by-four dataset identifier.

    Returns:
        The catalog row as a dict, or None if not found in the cache.

    Raises:
        FileNotFoundError: If the catalog cache has never been refreshed.
    """
    if not CATALOG_PARQUET.exists():
        raise FileNotFoundError(
            f"No catalog cache at {CATALOG_PARQUET}. Run scripts/refresh_catalog.py first."
        )
    df = pd.read_parquet(CATALOG_PARQUET)
    matches = df[df["id"] == dataset_id]
    if matches.empty:
        return None
    return _plain_row(matches.iloc[0].to_dict())
