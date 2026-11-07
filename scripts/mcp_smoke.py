#!/usr/bin/env python3
"""Smoke test the Cambridge Open Data MCP server end-to-end over stdio.

Spawns the server exactly as opencode launches it (``uv run cambridge-open-data-ma-mcp``)
and drives every tool and resource, asserting the behaviour that matters most for
a public release: that the gotcha-defending guards actually fire and that tool
output is JSON-serialisable end to end. Because it exercises the same launch
command opencode.json registers, a green run also proves that config is valid.

Cache semantics
---------------
The discovery, coverage, and cross-reference checks exercise data that lives in
the local Parquet cache (``data/catalog.parquet`` plus a few raw pulls). On a
machine with a populated cache -- the maintainer's, or a developer who has run
the setup -- every check runs: **14/14**. On a fresh clone with no cache, those
checks **SKIP** (not fail) with a message, and the cache-free checks (the
server starts, exposes its resources) still run. A skip is *not* a failure, so a
fresh clone exits 0. To run the full suite, populate the cache first:

    uv run scripts/refresh_catalog.py
    uv run scripts/fetch_dataset.py 9qm7-wbdc
    uv run scripts/fetch_dataset.py ixg8-tyau
    uv run scripts/fetch_dataset.py 5bn4-5wey

(the ``data/raw/*.parquet`` files can also be copied from the
``local-data-experiments`` repo.) The skip banner prints these exact commands.

Usage:
    uv run scripts/mcp_smoke.py

Exit codes:
    0 no checks failed (skips do not count as failures)
    1 one or more checks failed (or the server would not start)
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from cambridge_data.config import cache_dir

# Raw datasets the coverage / cross-reference checks exercise. A fresh clone
# has none of these, so those checks skip until they are pulled.
_RAW_DATASETS = ("9qm7-wbdc", "ixg8-tyau", "5bn4-5wey")


@dataclass
class Report:
    """Running tally of smoke-test checks, skips, and failures."""

    failures: int = 0
    checks: int = 0
    skips: int = 0

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        """Record and print one check, incrementing the tally."""
        self.checks += 1
        if not ok:
            self.failures += 1
        status = "PASS" if ok else "FAIL"
        suffix = f" -- {detail}" if detail else ""
        print(f"  [{status}] {name}{suffix}")

    def skip(self, name: str, reason: str = "") -> None:
        """Record a check that was not run because its cache is absent.

        Args:
            name: The check that would have run, for parity with the full suite.
            reason: An actionable message (usually the command that populates it).
        """
        self.skips += 1
        suffix = f" -- {reason}" if reason else ""
        print(f"  [SKIP] {name}{suffix}")


def cache_status() -> tuple[bool, dict[str, bool]]:
    """Report which caches the local data directory currently holds.

    Returns:
        A ``(catalog_present, {dataset_id: present})`` tuple. The cache location
        honours ``CAM_OPEN_DATA_CACHE_DIR`` (via :func:`cambridge_data.config.cache_dir`).
    """
    raw_dir = cache_dir() / "raw"
    catalog = (cache_dir() / "catalog.parquet").exists()
    raw = {id: (raw_dir / f"{id}.parquet").exists() for id in _RAW_DATASETS}
    return catalog, raw


def _fetch_hint(dataset_id: str) -> str:
    """The command that populates one raw dataset cache."""
    return f"uv run scripts/fetch_dataset.py {dataset_id}"


async def call(session: ClientSession, name: str, args: dict[str, Any]):
    """Call a tool, returning the raw result for error inspection."""
    return await session.call_tool(name, args)


def payload(result: Any) -> dict[str, Any]:
    """Parse the first JSON text block of a tool result into a dict.

    Args:
        result: A CallToolResult returned by ``call_tool``.

    Returns:
        The parsed JSON object, or ``{"_raw": <text>}`` when the block is not
        JSON (e.g. an error message).
    """
    text = "\n".join(block.text for block in result.content if getattr(block, "text", None))
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_raw": text}


async def exercise(
    session: ClientSession,
    report: Report,
    catalog_ok: bool,
    raw_ok: dict[str, bool],
) -> None:
    """Drive every tool and resource, recording one check per assertion.

    Cache-dependent checks skip (with a how-to message) when their cache is
    absent, so a fresh clone exits 0 without a populated cache.
    """
    # 1. Discovery -- the machine field names must surface (not the display names).
    if catalog_ok:
        data = payload(await call(session, "search_datasets", {"keyword": "parking", "limit": 3}))
        report.check(
            "search_datasets finds vnxa-cuyr",
            data.get("count", 0) > 0
            and any(r.get("id") == "vnxa-cuyr" for r in data.get("results", [])),
            f"count={data.get('count')}",
        )
        report.check(
            "search_datasets surfaces machine field names",
            all(r.get("columns_field_name") for r in data.get("results", [])),
        )
    else:
        report.skip(
            "search_datasets (needs data/catalog.parquet)", "uv run scripts/refresh_catalog.py"
        )

    # 2. Schema + coverage profile, honestly reporting whether it is cached.
    if catalog_ok:
        data = payload(
            await call(session, "describe_dataset", {"dataset_id": "vnxa-cuyr", "probe": True})
        )
        report.check(
            "describe_dataset returns full schema",
            data.get("name") == "Cambridge Parking Tickets"
            and bool(data.get("columns_field_name")),
            f"cols={len(data.get('columns_field_name', []))}",
        )
        report.check(
            "describe_dataset reports cached status honestly",
            "cached" in data,
            f"cached={data.get('cached')}",
        )
    else:
        report.skip(
            "describe_dataset (needs data/catalog.parquet)", "uv run scripts/refresh_catalog.py"
        )

    # 3. Automated field-population audit -- the recent-window defence, hands-free.
    #    Building permits (9qm7-wbdc) reliably carries partly-populated fields;
    #    the fully-populated budget datasets (ixg8-tyau, 5bn4-5wey) flag nothing.
    field: str | None = None
    if raw_ok.get("9qm7-wbdc"):
        data = payload(await call(session, "coverage_audit", {"dataset_id": "9qm7-wbdc", "top": 4}))
        flags = data.get("flags", [])
        report.check(
            "coverage_audit flags partly-populated fields",
            bool(flags),
            f"flagged {len(flags)} fields",
        )
        field = flags[0]["field"] if flags else None
    else:
        report.skip("coverage_audit (needs data/raw/9qm7-wbdc.parquet)", _fetch_hint("9qm7-wbdc"))

    # 4. A single-field probe on the top flag, stating its populated fraction.
    #    Runs only when check 3 ran and found a flag; otherwise it is silent.
    if field is not None:
        data = payload(
            await call(session, "field_coverage", {"dataset_id": "9qm7-wbdc", "field": field})
        )
        report.check(
            "field_coverage reports populated_pct",
            isinstance(data.get("populated_pct"), (int, float)),
            f"{field}={data.get('populated_pct')}%",
        )
        report.check(
            "field_coverage states a window warning when applicable",
            bool(data.get("warning")),
            "warning present" if data.get("warning") else "no warning",
        )

    # 5. Cross-dataset SQL -- numpy numerics must survive JSON end to end.
    if raw_ok.get("ixg8-tyau"):
        sql = (
            "SELECT department, COUNT(*) AS positions, "
            "ROUND(SUM(TRY_CAST(total_salary AS DOUBLE))) AS salary "
            "FROM ds_ixg8_tyau GROUP BY 1 ORDER BY 3 DESC LIMIT 3"
        )
        data = payload(await call(session, "query", {"sql": sql, "limit": 3}))
        if "error" in data:
            report.check("query runs cross-dataset SQL", False, data["error"])
        else:
            rows = data.get("rows", [])
            report.check(
                "query returns rows", data.get("row_count") == 3, f"rows={data.get('row_count')}"
            )
            if rows:
                head = rows[0]
                report.check(
                    "query coerces numpy -> JSON-native numerics",
                    isinstance(head.get("positions"), int)
                    and isinstance(head.get("salary"), (int, float)),
                    f"positions={head.get('positions')!r} salary={head.get('salary')!r}",
                )
    else:
        report.skip(
            "query cross-dataset SQL (needs data/raw/ixg8-tyau.parquet)", _fetch_hint("ixg8-tyau")
        )

    # 6. A display name (not a machine name) must raise an actionable error.
    if raw_ok.get("5bn4-5wey"):
        err = await call(
            session, "field_coverage", {"dataset_id": "5bn4-5wey", "field": "Total Expenditure"}
        )
        text = "\n".join(block.text for block in err.content if getattr(block, "text", None))
        low = text.lower()
        err_signalled = getattr(err, "isError", False)
        report.check(
            "wrong field name -> actionable error",
            err_signalled and ("available" in low or "not a column" in low),
            "error signalled" if err_signalled else "NO error -- expected a KeyError",
        )
    else:
        report.skip("field_coverage wrong-name error (needs data/raw/5bn4-5wey.parquet)",
                    _fetch_hint("5bn4-5wey"))

    # 7. Resources: the corpus as addressable context.
    uris = [str(r.uri) for r in (await session.list_resources()).resources]
    turis = [t.uriTemplate for t in (await session.list_resource_templates()).resourceTemplates]
    report.check("resources include cambridge://catalog", "cambridge://catalog" in uris, f"{uris}")
    report.check(
        "templates include dataset and report profiles",
        any("datasets/{" in t for t in turis) and any("reports/{" in t for t in turis),
        f"{turis}",
    )
    rep = await session.read_resource("cambridge://reports")
    report.check(
        "read cambridge://reports lists slugs",
        bool(rep.contents and rep.contents[0].text.strip()),
    )
    if catalog_ok:
        prof = await session.read_resource("cambridge://datasets/ixg8-tyau")
        report.check(
            "read cambridge://datasets/ixg8-tyau returns profile",
            bool(prof.contents) and "columns_field_name" in prof.contents[0].text,
        )
    else:
        report.skip("read cambridge://datasets/ixg8-tyau (needs data/catalog.parquet)",
                    "uv run scripts/refresh_catalog.py")


async def main() -> int:
    """Spawn the server and run the smoke test, returning a process exit code."""
    catalog_ok, raw_ok = cache_status()
    missing = [id for id, present in raw_ok.items() if not present]
    if not catalog_ok or missing:
        print("Cache incomplete -- some checks will SKIP (not fail). To run the full suite:")
        if not catalog_ok:
            print("    uv run scripts/refresh_catalog.py")
        for dataset_id in missing:
            print(f"    {_fetch_hint(dataset_id)}")
        print("    (data/raw/*.parquet can also be copied from the local-data-experiments repo.)\n")

    params = StdioServerParameters(command="uv", args=["run", "cambridge-open-data-ma-mcp"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            report = Report()
            try:
                await exercise(session, report, catalog_ok, raw_ok)
            except Exception as exc:  # noqa: BLE001 -- report as a failure, don't crash
                report.check(f"unexpected error: {type(exc).__name__}", False, str(exc))

    passed = report.checks - report.failures
    suffix = f", {report.skips} skipped" if report.skips else ""
    print(f"\n{passed}/{report.checks} checks passed{suffix}")
    return 0 if report.failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
