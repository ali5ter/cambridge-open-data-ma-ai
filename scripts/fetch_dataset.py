#!/usr/bin/env python3
"""Fetch a Cambridge Open Data dataset and cache it as Parquet.

Pulls every row of a dataset via the SODA API (paginated) and writes it to
data/raw/<dataset_id>.parquet, recording the fetch in data/manifest.json.
Safe to re-run -- overwrites the prior cache for that dataset id.

The fetch itself lives in cambridge_data.fetch so the MCP server (which shares
this one implementation) and this CLI stay in sync; this script only parses
arguments and reports the result.

Author: Alister Lewis-Bowen <alister@lewis-bowen.org>
Version: 1.0.0
Date: 2026-11-06
License: MIT

Usage:
    uv run scripts/fetch_dataset.py ixg8-tyau
    uv run scripts/fetch_dataset.py ixg8-tyau --where "fiscal_year='2027'"
    uv run scripts/fetch_dataset.py ixg8-tyau --select "department,total_salary"

Exit codes:
    0 success
    1 fetch or write failure
"""

from __future__ import annotations

import argparse
import sys

from rich.console import Console

from cambridge_data.fetch import fetch

console = Console()
error_console = Console(stderr=True)


def main() -> int:
    """Fetch a dataset from the CLI and report the result.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_id", help="Socrata four-by-four dataset id, e.g. ixg8-tyau")
    parser.add_argument("--where", help="SoQL $where filter", default=None)
    parser.add_argument("--select", help="SoQL $select projection", default=None)
    args = parser.parse_args()

    try:
        record = fetch(args.dataset_id, where=args.where, select=args.select)
    except Exception as exc:  # noqa: BLE001 -- top-level CLI error boundary
        error_console.print(f"[red]✗[/red] failed to fetch {args.dataset_id}: {exc}")
        return 1

    console.print(f"[green]✔[/green] cached {record['rows']} rows -> {record['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
