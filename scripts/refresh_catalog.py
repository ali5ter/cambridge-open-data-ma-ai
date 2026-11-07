#!/usr/bin/env python3
"""Refresh the local cache of the Cambridge Open Data catalog.

Pulls the full dataset listing (name, description, columns, tags, update
frequency) from the Socrata Discovery API and snapshots it to
data/catalog.parquet for fast offline search via search_catalog.py.

Usage:
    uv run scripts/refresh_catalog.py

Exit codes:
    0 success
    1 refresh failure
"""

from __future__ import annotations

import sys

from cambridge_data.catalog import refresh_catalog


def main() -> int:
    """Refresh the catalog cache and report the result.

    Returns:
        Process exit code.
    """
    try:
        count = refresh_catalog()
    except Exception as exc:  # noqa: BLE001 -- top-level CLI error boundary
        print(f"error: catalog refresh failed: {exc}", file=sys.stderr)
        return 1
    print(f"cached {count} datasets -> data/catalog.parquet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
