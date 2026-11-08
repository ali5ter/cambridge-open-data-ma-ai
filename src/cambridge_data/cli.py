#!/usr/bin/env python3
"""cambridge-data -- a cohesive CLI front end to the Cambridge Open Data toolkit.

A single ``cambridge-data`` command with one subcommand per MCP tool (plus the
four opencode-native resources), so a human can do from the shell everything an
agent does through the MCP server -- and the two never drift, because both call
the same library in :mod:`cambridge_data`. This is the "one library driving two
entry points" story made literal: the CLI and the server are two thin skins over
``cambridge_data``.

Commands (mirroring the server's eight tools and four resources):

    refresh                refresh the local catalog cache from the live Discovery API
    search KEYWORD         find datasets by keyword (name, description, category, tags)
    describe DATASET_ID    one dataset's schema + coverage profile
    fetch DATASET_ID       pull a dataset's rows and cache them as Parquet
    coverage DATASET_ID    probe how ONE field is populated (the recent-window defence)
    audit DATASET_ID       scan EVERY field, least-populated first
    cached                 list the dataset ids cached locally
    query SQL              run a DuckDB SELECT across the cached ds_* views
    catalog                dump the full compact dataset index (cambridge://catalog)
    reports / report SLUG  the cambridge://reports and cambridge://reports/{slug} resources

Every command accepts ``--json`` for machine-readable output (pipe it to another
tool). Long-running network work (``refresh``, ``fetch``) shows a spinner;
results render as Rich tables; errors print to stderr with a non-zero exit and
tell you the fix. The per-operation ``scripts/`` helpers remain as the by-hand
equivalents of these subcommands.

Author: Alister Lewis-Bowen <alister@lewis-bowen.org>
Version: 1.0.0
Date: 2026-11-08
License: MIT

Usage:
    cambridge-data search "budget salaries"
    cambridge-data describe ixg8-tyau --probe
    cambridge-data fetch ixg8-tyau --where "fiscal_year='2027'"
    cambridge-data audit ixg8-tyau --threshold 99 --top 10
    cambridge-data query "SELECT department, SUM(TRY_CAST(total_salary AS DOUBLE)) s
                          FROM ds_ixg8_tyau GROUP BY 1 ORDER BY 2 DESC LIMIT 3"
    cambridge-data search budget --json

Exit codes:
    0 - success
    1 - a command failed (network, missing cache, bad SQL, unknown field/slug)
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from itertools import zip_longest

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from cambridge_data.catalog import refresh_catalog, search
from cambridge_data.config import cache_dir, reports_dir
from cambridge_data.fetch import fetch
from cambridge_data.guards import coverage_audit, dataset_profile, field_coverage
from cambridge_data.warehouse import connect, list_cached_datasets

console = Console()
err = Console(stderr=True)

# A module-level em dash: a backslash escape is not allowed inside an f-string
# expression on Python 3.11 (this project's minimum), so the placeholder is a
# named constant rather than a "\u2014" literal inside the f-string braces.
_DASH = "\u2014"


# --------------------------------------------------------------------------- #
# Output helpers
# --------------------------------------------------------------------------- #
def _dump_json(obj: object) -> None:
    """Print a JSON-native structure to stdout for piping to another tool.

    Args:
        obj: Any JSON-serialisable structure (``default=str`` coerces the rare
            non-serializable value, e.g. a stray datetime).
    """
    console.print(json.dumps(obj, indent=2, default=str))


def _fields_table(profile: object) -> Table:
    """Build the schema table for a dataset profile.

    Args:
        profile: A :class:`cambridge_data.guards.DatasetProfile`.

    Returns:
        A Rich table of display name, machine field name, and type.
    """
    table = Table(title="fields", header_style="bold cyan", expand=False)
    table.add_column("display", style="white")
    table.add_column("machine (query with this)", style="magenta")
    table.add_column("type", style="dim")
    for disp, machine, typ in zip_longest(
        profile.columns_name,  # type: ignore[attr-defined]
        profile.columns_field_name,  # type: ignore[attr-defined]
        profile.columns_datatype,  # type: ignore[attr-defined]
    ):
        table.add_row(disp or "\u2014", machine or "\u2014", typ or "\u2014")
    return table


def _coverage_table(flags: list[object]) -> Table:
    """Build a table of partly-populated fields, least-populated first.

    Args:
        flags: A list of :class:`cambridge_data.guards.FieldCoverage`.

    Returns:
        A Rich table of field, populated fraction, and the populated window.
    """
    table = Table(
        title="[yellow]coverage traps[/yellow] -- fields populated for only a recent window",
        header_style="bold yellow",
        expand=False,
    )
    table.add_column("field", style="magenta")
    table.add_column("populated", justify="right")
    table.add_column("window", style="dim")
    for flag in flags:
        fc = flag  # a FieldCoverage
        window = f"{fc.earliest_date}..{fc.latest_date}" if fc.earliest_date else "\u2014"
        table.add_row(fc.field, f"{fc.populated_pct:.1f}%", window)
    return table


# --------------------------------------------------------------------------- #
# Command handlers
# --------------------------------------------------------------------------- #
def cmd_refresh(args: argparse.Namespace) -> int:
    """Refresh the catalog cache and report the row count written."""
    with console.status("[cyan]refreshing catalog from the live Discovery API\u2026[/cyan]"):
        count = refresh_catalog()
    path = cache_dir() / "catalog.parquet"
    if args.as_json:
        _dump_json({"datasets": count, "path": str(path)})
    else:
        console.print(
            f"[green]\u2714[/green] cached [bold]{count}[/bold] datasets -> [cyan]{path}[/cyan]"
        )
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    """Search the cached catalog and render the matches as a table."""
    results = search(args.keyword, limit=args.limit)
    if args.as_json:
        _dump_json({"keyword": args.keyword, "count": len(results), "results": results})
        return 0
    if not results:
        console.print(
            f"[yellow]![/yellow] no datasets match [bold]{args.keyword!r}[/bold] "
            "-- run `cambridge-data refresh` if the cache looks stale"
        )
        return 0
    table = Table(
        title=f"datasets matching [bold]{args.keyword}[/bold] ({len(results)})",
        header_style="bold cyan",
        expand=False,
    )
    table.add_column("id", style="magenta", no_wrap=True)
    table.add_column("name")
    table.add_column("category", style="dim")
    for row in results:
        table.add_row(row.get("id", ""), row.get("name", ""), row.get("category", "") or "\u2014")
    console.print(table)
    console.print(
        "[dim]run `cambridge-data describe <id>` for a dataset's fields and coverage[/dim]"
    )
    return 0


def cmd_describe(args: argparse.Namespace) -> int:
    """Render one dataset's schema-and-coverage profile."""
    profile = dataset_profile(args.dataset_id, probe=args.probe, top=args.top)
    if args.as_json:
        _dump_json(asdict(profile))
        return 0

    summary = [f"[bold]{profile.name or '(unnamed)'}[/bold]"]
    if profile.category:
        summary.append(f"[dim]{profile.category}[/dim]")
    summary.append(
        f"update: [cyan]{profile.update_frequency or _DASH}[/cyan]"
        f"   last updated: [cyan]{profile.data_updated_at or _DASH}[/cyan]"
    )
    if profile.cached:
        window = (
            f"{profile.earliest_date}..{profile.latest_date}" if profile.earliest_date else "\u2014"
        )
        summary.append(
            f"[green]\u2714 cached[/green] [bold]{profile.row_count:,}[/bold] rows, "
            f"[dim]{window}[/dim]"
        )
    else:
        summary.append(
            f"[yellow]\u2717 not cached[/yellow] -- run `cambridge-data fetch "
            f"{profile.dataset_id}` for coverage + date range"
        )
    console.print(
        Panel("\n".join(summary), title=f"[cyan]{profile.dataset_id}[/cyan]", border_style="cyan")
    )
    console.print(_fields_table(profile))
    if profile.coverage_flags:
        console.print(_coverage_table(list(profile.coverage_flags)))
    elif args.probe:
        console.print("[green]\u2714[/green] all fields fully populated -- no recent-window traps")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    """Pull a dataset's rows into the Parquet cache."""
    with console.status(f"[cyan]fetching {args.dataset_id}\u2026[/cyan]"):
        record = fetch(args.dataset_id, where=args.where, select=args.select)
    if args.as_json:
        _dump_json(record)
    else:
        console.print(
            f"[green]\u2714[/green] cached [bold]{record['rows']:,}[/bold] rows -> "
            f"[cyan]{record['path']}[/cyan]"
        )
    return 0


def cmd_coverage(args: argparse.Namespace) -> int:
    """Probe how one field is populated across a cached dataset."""
    probe = field_coverage(args.dataset_id, args.field, date_field=args.date_field)
    if args.as_json:
        _dump_json(asdict(probe))
        return 0
    status = "yellow" if probe.warning else "green"
    window = f"{probe.earliest_date}..{probe.latest_date}" if probe.earliest_date else "\u2014"
    body = [
        f"field [bold]{probe.field}[/bold] in [cyan]{probe.dataset_id}[/cyan]",
        f"populated: [bold]{probe.populated_pct:.1f}%[/bold] "
        f"({probe.populated_rows:,} of {probe.total_rows:,} rows)",
        f"date field: [dim]{probe.date_field or _DASH}[/dim]   window: [dim]{window}[/dim]",
    ]
    console.print(Panel("\n".join(body), title="[cyan]field coverage[/cyan]", border_style=status))
    if probe.warning:
        console.print(f"[yellow]![/yellow] {probe.warning}")
    else:
        console.print("[green]\u2714[/green] fully populated -- safe to sum/rate over all rows")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    """Flag every partly-populated field, least-populated first."""
    flags = coverage_audit(args.dataset_id, threshold=args.threshold, top=args.top)
    if args.as_json:
        _dump_json(
            {
                "dataset_id": args.dataset_id,
                "count": len(flags),
                "flags": [asdict(flag) for flag in flags],
            }
        )
        return 0
    if not flags:
        console.print(
            f"[green]\u2714[/green] all fields in [bold]{args.dataset_id}[/bold] "
            f"are fully populated (\u2265 {args.threshold:.0f}%)"
        )
        return 0
    console.print(_coverage_table(flags))
    console.print(
        f"[yellow]![/yellow] {len(flags)} field(s) below {args.threshold:.0f}% populated "
        "-- treat any total/rate over them as windowed, not complete"
    )
    return 0


def cmd_cached(args: argparse.Namespace) -> int:
    """List the dataset ids cached under data/raw/."""
    cached = list_cached_datasets()
    if args.as_json:
        _dump_json({"cached": cached})
        return 0
    if not cached:
        console.print(
            "[yellow]![/yellow] nothing cached yet -- run `cambridge-data fetch <id>` "
            "(or `refresh` to populate the catalog first)"
        )
        return 0
    console.print(
        f"[green]\u2714[/green] [bold]{len(cached)}[/bold] dataset(s) cached under "
        f"[cyan]{cache_dir() / 'raw'}[/cyan]:"
    )
    console.print(", ".join(cached))
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    """Run a DuckDB SELECT across the cached ds_* views."""
    connection = connect()
    try:
        frame = connection.execute(args.sql).fetchdf()
    except Exception as exc:  # noqa: BLE001 -- surface DuckDB errors as an exit code
        if args.as_json:
            _dump_json({"error": str(exc), "sql": args.sql})
        else:
            err.print(f"[red]\u2717[/red] query failed: {exc}")
        return 1
    finally:
        connection.close()

    limited = frame.head(args.limit)
    rows = json.loads(limited.to_json(orient="records", date_format="iso", double_precision=15))
    if args.as_json:
        _dump_json({"columns": list(frame.columns), "row_count": len(rows), "rows": rows})
        return 0
    if not rows:
        console.print("[yellow]![/yellow] 0 rows returned")
        return 0
    columns = list(frame.columns)
    table = Table(
        title=f"query -- [bold]{len(rows):,}[/bold] row(s)", header_style="bold cyan", expand=False
    )
    for column in columns:
        numeric = str(frame[column].dtype).startswith(("int", "float"))
        table.add_column(str(column), justify="right" if numeric else "left")
    for row in rows:
        cells = ["" if row.get(column) is None else str(row.get(column)) for column in columns]
        table.add_row(*cells)
    console.print(table)
    return 0


def cmd_catalog(args: argparse.Namespace) -> int:
    """Dump the full compact dataset index (the cambridge://catalog resource)."""
    limit = args.limit if args.limit and args.limit > 0 else 100_000
    rows = search("", limit=limit)
    if args.as_json:
        _dump_json(
            [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "category": row.get("category", ""),
                    "update_frequency": row.get("update_frequency", ""),
                    "data_updated_at": row.get("data_updated_at", ""),
                }
                for row in rows
            ]
        )
        return 0
    if not rows:
        console.print("[yellow]![/yellow] catalog is empty -- run `cambridge-data refresh` first")
        return 0
    table = Table(
        title=f"catalog -- [bold]{len(rows):,}[/bold] dataset(s)",
        header_style="bold cyan",
        expand=False,
    )
    table.add_column("id", style="magenta", no_wrap=True)
    table.add_column("name")
    table.add_column("category", style="dim")
    for row in rows:
        table.add_row(row.get("id", ""), row.get("name", ""), row.get("category", "") or "\u2014")
    console.print(table)
    return 0


def cmd_reports(args: argparse.Namespace) -> int:
    """List the finished analysis-report slugs (the cambridge://reports resource)."""
    rdir = reports_dir()
    slugs = sorted(p.name for p in rdir.glob("*") if p.is_dir())
    if args.as_json:
        _dump_json(slugs)
        return 0
    if not slugs:
        console.print(
            f"[yellow]![/yellow] no reports in [cyan]{rdir}[/cyan] (the corpus lives in the "
            "upstream local-data-experiments repo; a fresh install has none)"
        )
        return 0
    console.print(f"[green]\u2714[/green] [bold]{len(slugs)}[/bold] report(s):")
    for slug in slugs:
        console.print(f"  [cyan]{slug}[/cyan]")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Print one finished report's Markdown (the cambridge://reports/{slug} resource)."""
    path = reports_dir() / args.slug / "report.md"
    if not path.exists():
        available = sorted(p.name for p in reports_dir().glob("*") if p.is_dir())
        if args.as_json:
            _dump_json({"error": f"unknown report slug {args.slug!r}", "available": available})
        else:
            err.print(
                f"[red]\u2717[/red] unknown report slug {args.slug!r}. "
                f"Available: {', '.join(available) or '(none)'}"
            )
        return 1
    text = path.read_text(encoding="utf-8")
    if args.as_json:
        _dump_json({"slug": args.slug, "markdown": text})
        return 0
    console.print(Markdown(text))
    return 0


# --------------------------------------------------------------------------- #
# Argument parsing and dispatch
# --------------------------------------------------------------------------- #
def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level parser with one subcommand per server tool/resource.

    Returns:
        The configured :class:`argparse.ArgumentParser`.
    """
    parser = argparse.ArgumentParser(
        prog="cambridge-data",
        description="Cohesive CLI over the Cambridge Open Data toolkit -- "
        "one subcommand per MCP tool.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", metavar="command")

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "-j",
            "--json",
            dest="as_json",
            action="store_true",
            help="Emit machine-readable JSON instead of Rich tables.",
        )

    p = sub.add_parser("refresh", help="refresh the local catalog cache")
    add_common(p)
    p.set_defaults(func=cmd_refresh)

    p = sub.add_parser("search", help="find datasets by keyword")
    p.add_argument("keyword", help="free-text search term")
    p.add_argument("--limit", type=int, default=20, help="max results (default 20)")
    add_common(p)
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("describe", help="one dataset's schema + coverage")
    p.add_argument("dataset_id", help="Socrata four-by-four dataset id, e.g. ixg8-tyau")
    p.add_argument("--probe", action="store_true", help="include coverage flags")
    p.add_argument("--top", type=int, default=10, help="max coverage flags (default 10)")
    add_common(p)
    p.set_defaults(func=cmd_describe)

    p = sub.add_parser("fetch", help="pull a dataset's rows and cache them")
    p.add_argument("dataset_id", help="Socrata four-by-four dataset id, e.g. ixg8-tyau")
    p.add_argument("--where", default=None, help="SoQL $where filter (server-side)")
    p.add_argument("--select", default=None, help="SoQL $select projection (server-side)")
    add_common(p)
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("coverage", help="probe how ONE field is populated")
    p.add_argument("dataset_id", help="Socrata four-by-four dataset id (must be cached)")
    p.add_argument("--field", required=True, help="machine field name (columns_field_name)")
    p.add_argument(
        "--date-field",
        default=None,
        help="time-axis column to bracket the populated rows (auto-detected when omitted)",
    )
    add_common(p)
    p.set_defaults(func=cmd_coverage)

    p = sub.add_parser("audit", help="scan EVERY field, least-populated first")
    p.add_argument("dataset_id", help="Socrata four-by-four dataset id (must be cached)")
    p.add_argument(
        "--threshold",
        type=float,
        default=99.0,
        help="flag fields below this %% populated (default 99.0)",
    )
    p.add_argument("--top", type=int, default=10, help="max fields to return (default 10)")
    add_common(p)
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("cached", help="list cached dataset ids")
    add_common(p)
    p.set_defaults(func=cmd_cached)

    p = sub.add_parser("query", help="run a DuckDB SELECT across cached ds_* views")
    p.add_argument("sql", help="a DuckDB SELECT referencing ds_<id> views")
    p.add_argument("--limit", type=int, default=1000, help="max rows to return (default 1000)")
    add_common(p)
    p.set_defaults(func=cmd_query)

    p = sub.add_parser("catalog", help="dump the full compact dataset index")
    p.add_argument("--limit", type=int, default=50, help="rows to show (0 = all; default 50)")
    add_common(p)
    p.set_defaults(func=cmd_catalog)

    p = sub.add_parser("reports", help="list finished report slugs")
    add_common(p)
    p.set_defaults(func=cmd_reports)

    p = sub.add_parser("report", help="print one finished report's Markdown")
    p.add_argument("slug", help="report directory name (from `cambridge-data reports`)")
    add_common(p)
    p.set_defaults(func=cmd_report)

    return parser


def main() -> int:
    """Parse the CLI, dispatch to the subcommand, and translate errors to exit codes.

    Returns:
        Process exit code -- 0 on success, 1 on command failure, 2 on a usage error.
    """
    parser = _build_parser()
    args = parser.parse_args()
    if not getattr(args, "command", None):
        parser.print_help()
        return 2
    try:
        return int(args.func(args) or 0)
    except KeyboardInterrupt:
        err.print("\n[red]\u2717[/red] interrupted")
        return 130
    except Exception as exc:  # noqa: BLE001 -- top-level CLI error boundary
        err.print(f"[red]\u2717[/red] {exc}")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
