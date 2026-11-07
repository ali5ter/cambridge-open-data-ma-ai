#!/usr/bin/env python3
"""Search the cached Cambridge Open Data catalog by keyword.

Usage:
    uv run scripts/search_catalog.py "police"
    uv run scripts/search_catalog.py "budget" --limit 5

Exit codes:
    0 success
    1 search failure (e.g. catalog cache missing -- run refresh_catalog.py first)
"""

from __future__ import annotations

import argparse
import sys

from cambridge_data.catalog import search


def main() -> int:
    """Search the catalog cache and print matches.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("keyword", help="Free-text search term")
    parser.add_argument("--limit", type=int, default=20, help="Max results (default: 20)")
    args = parser.parse_args()

    try:
        results = search(args.keyword, limit=args.limit)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not results:
        print("no matches")
        return 0

    for row in results:
        print(f"{row['id']}  {row['name']}  [{row['category']}]  views={row['page_views_total']}")
        print(f"    {row['link']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
