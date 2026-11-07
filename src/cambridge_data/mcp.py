"""MCP server exposing the Cambridge Open Data toolkit to agentic harnesses.

Wraps the ``cambridge_data`` library (catalog search/fetch, DuckDB
cross-referencing, and gotcha-defending coverage probes) as Model Context
Protocol tools and resources, so any MCP client -- opencode, Claude Code, or a
standalone agent -- can discover datasets, pull them, and cross-reference them
without shelling out and parsing text.

Run it as a stdio server:

    uv run python -m cambridge_data.mcp

Register it with opencode (project config by default, ``--global`` for the
global config):

    opencode mcp add cambridge-open-data-ma-ai -- uv run cambridge-open-data-ma-mcp

The server holds no state of its own: each query opens a fresh warehouse
connection over ``data/raw/*.parquet``, so it reflects the cache as of the call
and honours this repo's "no separate warehouse to keep in sync" decision.

Author: Alister Lewis-Bowen <alister@lewis-bowen.org>
Version: 1.0.0
Date: 2026-11-06
License: MIT
"""

from __future__ import annotations

import json
from dataclasses import asdict

from mcp.server.fastmcp import FastMCP

from cambridge_data.catalog import refresh_catalog, search
from cambridge_data.config import cache_dir, reports_dir
from cambridge_data.fetch import fetch
from cambridge_data.guards import coverage_audit, dataset_profile, field_coverage
from cambridge_data.warehouse import connect, list_cached_datasets

REPORTS_DIR = reports_dir()

mcp = FastMCP("cambridge-open-data-ma-mcp")


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #
@mcp.tool(
    name="refresh_catalog",
    description=(
        "Refresh the local catalog cache from the live Socrata Discovery API. "
        "Pulls the full dataset listing (~280 datasets: id, name, description, "
        "fields, tags, update cadence) into data/catalog.parquet. Run first if "
        "search_datasets reports a missing cache, or when the portal may have new "
        "datasets. Needs no credentials; the app token in .env only lifts the "
        "anonymous rate limit. Returns the count of datasets cached."
    ),
)
def refresh_catalog_tool() -> dict[str, object]:
    """Refresh and report the local catalog cache.

    Returns:
        A dict with ``datasets`` (count written) and ``path`` (the cache file).
    """
    count = refresh_catalog()
    return {"datasets": count, "path": str(cache_dir() / "catalog.parquet")}


@mcp.tool(
    description=(
        "Search the cached dataset catalog by keyword. Matches name, description, "
        "category, and tags. Returns each result's id, name, category, link, and "
        "-- crucially -- columns_field_name, the *machine* field names a query "
        "actually accepts (NOT columns_name, the human display names; querying with "
        "a display name silently returns zero rows). Use this to find a dataset, "
        "then describe_dataset to get its full schema before querying."
    )
)
def search_datasets(keyword: str, limit: int = 20) -> dict[str, object]:
    """Search the catalog for datasets matching a keyword.

    Args:
        keyword: Free-text search term (case-insensitive substring).
        limit: Maximum results to return.

    Returns:
        A dict with ``results`` -- a list of matching dataset rows, each with id,
        name, category, link, update_frequency, and columns_field_name.
    """
    matches = search(keyword, limit=limit)
    results = [
        {
            "id": row["id"],
            "name": row["name"],
            "category": row.get("category", ""),
            "link": row.get("link", ""),
            "update_frequency": row.get("update_frequency", ""),
            "columns_field_name": row.get("columns_field_name", []),
        }
        for row in matches
    ]
    return {"keyword": keyword, "count": len(results), "results": results}


@mcp.tool(
    description=(
        "Full schema and coverage profile for one dataset. Returns the machine "
        "field names (query with these, not the display names), their types, "
        "display names, tags, update cadence, and -- when the dataset is cached -- "
        "the row count and the dataset's own earliest/latest date (the era-gap "
        "signal: a zero result for an old date may mean the dataset predates it, "
        "not that nothing happened). Set probe=true to also get coverage_flags: "
        "fields that are only partly populated -- the recent-window traps to check "
        "before trusting any total or rate."
    )
)
def describe_dataset(dataset_id: str, probe: bool = False) -> dict[str, object]:
    """Build and return a dataset's schema-and-coverage profile.

    Args:
        dataset_id: Socrata four-by-four dataset identifier.
        probe: When true, include coverage flags (partly-populated fields).

    Returns:
        The :class:`DatasetProfile` as a dict.
    """
    profile = dataset_profile(dataset_id, probe=probe)
    return asdict(profile)


@mcp.tool(
    name="fetch_dataset",
    description=(
        "Pull every row of a dataset via the SODA API and cache it as Parquet "
        "(data/raw/<id>.parquet), so it can be cross-referenced in SQL. Supports "
        "a server-side $where filter and $select projection. Re-running overwrites "
        "the cache; check describe_dataset's cached/fetched_at first to avoid "
        "re-pulling time-sensitive data unnecessarily. Large datasets (millions of "
        "rows) take time; prefer a $where filter when a subset suffices."
    ),
)
def fetch_dataset_tool(
    dataset_id: str,
    where: str | None = None,
    select: str | None = None,
) -> dict[str, object]:
    """Fetch a dataset and cache it as Parquet.

    Args:
        dataset_id: Socrata four-by-four dataset identifier.
        where: Optional SoQL ``$where`` filter, applied server-side.
        select: Optional SoQL ``$select`` projection, applied server-side.

    Returns:
        A record with dataset_id, rows (count written), path, and fetched_at.
    """
    return fetch(dataset_id, where=where, select=select)


@mcp.tool(
    name="field_coverage",
    description=(
        "Probe how ONE field is actually populated across a cached dataset -- the "
        "defence against the recent-window trap. Reports the populated fraction and, "
        "for populated rows, the date range they span, and states a warning when the "
        "pattern looks like a recent operational window rather than the full history "
        "(e.g. a 'balance' field only filled for the last year). Always run this "
        "before summing or rate-computing over a field. The field must be a machine "
        "name from columns_field_name; a display name raises an actionable error "
        "listing the real fields."
    ),
)
def field_coverage_tool(
    dataset_id: str,
    field: str,
    date_field: str | None = None,
) -> dict[str, object]:
    """Probe how one field is populated across a cached dataset.

    Args:
        dataset_id: Socrata four-by-four dataset identifier (must be cached).
        field: The field to probe, by its machine name.
        date_field: The time-axis column to bracket the populated rows by.
            Auto-detected from the column names when omitted.

    Returns:
        The :class:`FieldCoverage` as a dict, including a ``warning`` string when
        the field looks like a recent window.
    """
    probe = field_coverage(dataset_id, field, date_field=date_field)
    return asdict(probe)


@mcp.tool(
    name="coverage_audit",
    description=(
        "Automated field-population audit: scan every field of a cached dataset and "
        "return the least-populated first -- the automated version of 'check field "
        "population before trusting a total'. This is how you discover, up front, "
        "that a 'complete-looking' column is really a recent window. Use it instead "
        "of hand-checking fields one at a time."
    ),
)
def coverage_audit_tool(
    dataset_id: str,
    threshold: float = 99.0,
    top: int = 10,
) -> dict[str, object]:
    """Flag every partly-populated field in a cached dataset.

    Args:
        dataset_id: Socrata four-by-four dataset identifier (must be cached).
        threshold: Flag fields whose populated fraction is below this percentage.
        top: Maximum fields to return, least-populated first.

    Returns:
        A dict with ``flags`` -- the :class:`FieldCoverage` of the least-populated
        fields, each with a ``warning``.
    """
    flags = coverage_audit(dataset_id, threshold=threshold, top=top)
    return {"dataset_id": dataset_id, "count": len(flags), "flags": [asdict(f) for f in flags]}


@mcp.tool(
    name="list_cached_datasets",
    description=(
        "List the dataset ids whose rows are cached locally in data/raw/. Only "
        "cached datasets can be queried in SQL or audited for coverage; use "
        "fetch_dataset to pull one that is not yet cached."
    ),
)
def list_cached_datasets_tool() -> dict[str, object]:
    """List the dataset ids cached under data/raw/.

    Returns:
        A dict with ``cached`` -- the sorted list of cached dataset ids.
    """
    return {"cached": list_cached_datasets()}


@mcp.tool(
    description=(
        "Run a DuckDB SELECT over the cached datasets, exposed as one SQL view per "
        "dataset named ds_<id_with_underscores> (e.g. ixg8-tyau -> ds_ixg8_tyau). "
        "This is the cross-referencing step: join/aggregate across ds_* views. Every "
        "Socrata column is a string -- use TRY_CAST(col AS DOUBLE) for numeric work, "
        "and expect join keys (e.g. department names) to need normalization before "
        "they line up. NOTE: runs arbitrary SQL over local Parquet only; a trusted "
        "single-user tool, not sandboxed. Prefer describe_dataset + coverage_audit "
        "first so you know the fields exist and are fully populated."
    )
)
def query(sql: str, limit: int = 1000) -> dict[str, object]:
    """Run a DuckDB SELECT over the cached ``ds_*`` views.

    Args:
        sql: A DuckDB SELECT query referencing ``ds_<id>`` views.
        limit: Maximum rows to return.

    Returns:
        A dict with ``columns`` and ``rows`` (each row a dict). On error, a dict
        with ``error`` and the failing SQL.
    """
    connection = connect()
    try:
        frame = connection.execute(sql).fetchdf()
    except Exception as exc:  # noqa: BLE001 -- surface DuckDB errors as tool output
        return {"error": str(exc), "sql": sql}
    finally:
        connection.close()

    # fetchdf() materialises numpy dtypes (int64, datetime64, arrays) that MCP
    # cannot JSON-serialise; round-trip through to_json to coerce to plain types.
    limited = frame.head(limit)
    rows = json.loads(limited.to_json(orient="records", date_format="iso", double_precision=15))
    return {"columns": list(frame.columns), "row_count": len(rows), "rows": rows}


# --------------------------------------------------------------------------- #
# Resources (opencode-native: list_mcp_resources / read_mcp_resource)
# --------------------------------------------------------------------------- #
@mcp.resource(
    "cambridge://catalog",
    description=(
        "The full dataset index for data.cambridgema.gov (~280 datasets). "
        "Compact: id, name, category, update frequency, and last-updated per "
        "dataset. Read this to discover datasets; use describe_dataset(id) for a "
        "single dataset's full schema and coverage."
    ),
    mime_type="application/json",
)
def resource_catalog() -> str:
    """Return the compact dataset index as JSON.

    Returns:
        A JSON string of every cached catalog row's key fields.
    """
    matches = search("", limit=10_000)
    index = [
        {
            "id": row["id"],
            "name": row["name"],
            "category": row.get("category", ""),
            "update_frequency": row.get("update_frequency", ""),
            "data_updated_at": row.get("data_updated_at", ""),
        }
        for row in matches
    ]
    return json.dumps(index, indent=2)


@mcp.resource(
    "cambridge://datasets/{dataset_id}",
    description=(
        "The full schema-and-coverage profile for one dataset: machine field "
        "names, types, display names, tags, update cadence, and (when cached) "
        "row count and date range. Read this before writing a query."
    ),
    mime_type="application/json",
)
def resource_dataset_profile(dataset_id: str) -> str:
    """Return one dataset's profile as JSON.

    Args:
        dataset_id: Socrata four-by-four dataset identifier (from the path).

    Returns:
        A JSON string of the :class:`DatasetProfile`.
    """
    profile = dataset_profile(dataset_id, probe=True)
    return json.dumps(asdict(profile), indent=2)


@mcp.resource(
    "cambridge://reports",
    description="The list of finished analysis reports in docs/reports/, by slug.",
    mime_type="application/json",
)
def resource_reports_index() -> str:
    """List available report slugs.

    Returns:
        A JSON string of report slug names (the docs/reports/<slug> directory
        names).
    """
    slugs = sorted(p.name for p in REPORTS_DIR.glob("*") if p.is_dir())
    return json.dumps(slugs, indent=2)


@mcp.resource(
    "cambridge://reports/{slug}",
    description="A finished analysis report's Markdown (self-contained, with provenance).",
    mime_type="text/markdown",
)
def resource_report(slug: str) -> str:
    """Return a finished report's Markdown.

    Args:
        slug: The report's directory name (from cambridge://reports).

    Returns:
        The report's Markdown text.

    Raises:
        ValueError: If the slug is not a known report. The message lists the
            available slugs.
    """
    report_path = REPORTS_DIR / slug / "report.md"
    if not report_path.exists():
        slugs = sorted(p.name for p in REPORTS_DIR.glob("*") if p.is_dir())
        raise ValueError(f"unknown report slug {slug!r}. Available: {', '.join(slugs) or '(none)'}")
    return report_path.read_text(encoding="utf-8")


def main() -> None:
    """Run the server over stdio (the transport opencode launches it with)."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
