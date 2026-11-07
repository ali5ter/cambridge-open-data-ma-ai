"""DuckDB warehouse over locally cached Cambridge Open Data parquet files.

Every dataset pulled via scripts/fetch_dataset.py lands in data/raw/<id>.parquet.
connect() opens an in-memory DuckDB connection with one view per cached
dataset, so cross-dataset analysis is plain SQL joins -- no separate
database file to keep in sync with the Parquet cache.
"""

from __future__ import annotations

import duckdb

from cambridge_data.config import cache_dir

RAW_DIR = cache_dir() / "raw"


def view_name(dataset_id: str) -> str:
    """Map a dataset id to its SQL view name.

    Args:
        dataset_id: Socrata four-by-four dataset identifier (e.g. "ixg8-tyau").

    Returns:
        A valid SQL identifier for the corresponding view (e.g. "ds_ixg8_tyau").
    """
    return f"ds_{dataset_id.replace('-', '_')}"


def connect() -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection with a view registered per cached dataset.

    Returns:
        A DuckDB connection. Query it directly, e.g.
        `con.sql("SELECT * FROM ds_ixg8_tyau LIMIT 5")`, or join across
        multiple `ds_*` views.
    """
    con = duckdb.connect()
    for path in sorted(RAW_DIR.glob("*.parquet")):
        escaped_path = str(path).replace("'", "''")
        con.execute(
            f"CREATE VIEW {view_name(path.stem)} AS SELECT * FROM read_parquet('{escaped_path}')"
        )
    return con


def list_cached_datasets() -> list[str]:
    """List dataset ids currently cached under data/raw/.

    Returns:
        Sorted list of dataset ids (Parquet filename stems).
    """
    return sorted(path.stem for path in RAW_DIR.glob("*.parquet"))
