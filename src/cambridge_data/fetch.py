"""Fetch a Cambridge Open Data dataset and cache it as Parquet.

Pulls every row of a dataset via the SODA API (paginated) and writes it to
``data/raw/<dataset_id>.parquet``, recording the fetch in
``data/manifest.json``. Safe to re-run -- overwrites the prior cache for that
dataset id.

This module owns the fetch so the CLI (``scripts/fetch_dataset.py``) and the MCP
server (``cambridge_data.mcp``) share one implementation instead of duplicating
it.

Author: Alister Lewis-Bowen <alister@lewis-bowen.org>
License: MIT
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pandas as pd

from cambridge_data.client import SodaClient
from cambridge_data.warehouse import RAW_DIR

MANIFEST_PATH = RAW_DIR.parent / "manifest.json"


def _load_manifest() -> dict[str, object]:
    """Load the fetch manifest, or an empty dict when it does not exist.

    Returns:
        The manifest mapping dataset id to its last-fetch record.
    """
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text())
    return {}


def _save_manifest(manifest: dict[str, object]) -> None:
    """Write the fetch manifest to disk.

    Args:
        manifest: The manifest mapping to persist.
    """
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True))


def fetch(
    dataset_id: str, *, where: str | None = None, select: str | None = None
) -> dict[str, object]:
    """Fetch all rows of a dataset and cache them as Parquet.

    Args:
        dataset_id: Socrata four-by-four dataset identifier.
        where: Optional SoQL ``$where`` filter applied server-side.
        select: Optional SoQL ``$select`` projection applied server-side.

    Returns:
        A record with ``dataset_id``, ``rows`` (the row count written), ``path``
        (the Parquet file written), and ``fetched_at`` (ISO 8601 timestamp).

    Raises:
        requests.HTTPError: If the SODA API request fails.
        FileNotFoundError: If the cache directory cannot be created.
    """
    client = SodaClient()
    rows = list(client.iter_all_rows(dataset_id, where=where, select=select))

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / f"{dataset_id}.parquet"
    pd.DataFrame(rows).to_parquet(out_path, index=False)

    fetched_at = datetime.now(UTC).isoformat()
    manifest = _load_manifest()
    manifest[dataset_id] = {
        "fetched_at": fetched_at,
        "row_count": len(rows),
        "where": where,
        "select": select,
    }
    _save_manifest(manifest)

    return {
        "dataset_id": dataset_id,
        "rows": len(rows),
        "path": str(out_path),
        "fetched_at": fetched_at,
    }
