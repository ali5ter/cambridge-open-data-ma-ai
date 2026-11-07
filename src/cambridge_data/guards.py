"""Gotcha-defending data probes for the Cambridge Open Data toolkit.

Turns recurring Socrata pitfalls into *default* behaviour instead of a memory the
caller must not forget:

* **Recent-window fields.** A column that looks complete but is only populated for
  the most recent operational window -- a blank cell then reads as "zero", when it
  really means "not tracked". ``field_coverage`` and ``coverage_audit`` state the
  populated fraction and the populated date range, so a caller can't silently sum a
  recent slice over the whole history.
* **Dataset-era gaps.** A current dataset (e.g. building permits) starts 2018-07; a
  search for 2016 returns nothing -- not because there was no work, but because the
  data predates the dataset. ``dataset_profile`` reports the dataset's own date
  range, so a zero result surfaces "era gap", not "nothing happened".
* **Wrong field name.** The catalog lists each column twice -- a *display* name and
  the *machine* field name. Querying with the display name returns zero rows silently,
  which reads as "no match". ``dataset_profile`` and ``field_coverage`` surface the
  real ``columns_field_name`` list and validate a requested field against it.

Every probe runs over the *locally cached* Parquet via pandas, so it is fast,
deterministic, and needs no network.

Author: Alister Lewis-Bowen <alister@lewis-bowen.org>
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from cambridge_data import catalog
from cambridge_data.warehouse import RAW_DIR

# Substrings that mark a column as the dataset's time axis.
_DATE_HINTS = ("date", "year", "time", "created", "updated", "period", "month", "day")


@dataclass(frozen=True)
class FieldCoverage:
    """A probe of how one field is actually populated across a dataset.

    Attributes:
        dataset_id: The Socrata dataset id the probe ran against.
        field: The probed field's machine name (``columns_field_name``).
        total_rows: Row count of the dataset.
        populated_rows: Rows where ``field`` is non-null and non-empty.
        populated_pct: ``populated_rows / total_rows`` as a percentage.
        date_field: The time-axis column used to bracket the populated rows, or
            ``None`` when the dataset has no obvious date column.
        earliest_date: Earliest populated-row date, or ``None``.
        latest_date: Latest populated-row date, or ``None``.
        warning: A non-empty string when the pattern looks like a recent-window
            trap; empty otherwise.
    """

    dataset_id: str
    field: str
    total_rows: int
    populated_rows: int
    populated_pct: float
    date_field: str | None
    earliest_date: str | None
    latest_date: str | None
    warning: str = ""

    @property
    def looks_like_window(self) -> bool:
        """True when the populated fraction is small enough to be a recent window."""
        return 0.0 < self.populated_pct < 99.0


def _read_cached(dataset_id: str) -> pd.DataFrame:
    """Load a dataset's cached Parquet, or raise with an actionable message.

    Args:
        dataset_id: Socrata four-by-four dataset identifier.

    Returns:
        The cached dataset as a DataFrame.

    Raises:
        FileNotFoundError: If the dataset was never fetched. The message tells the
            caller to run ``fetch_dataset`` and explains that probes run over the
            local cache, not the live API.
    """
    path = RAW_DIR / f"{dataset_id}.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"dataset {dataset_id!r} is not cached at {path}. Run fetch_dataset "
            f"(or scripts/fetch_dataset.py {dataset_id}) first -- the coverage "
            "probes run over locally cached Parquet, not the live API."
        )
    return pd.read_parquet(path)


def _primary_date_column(frame: pd.DataFrame) -> str | None:
    """Return the first column whose name looks like a time axis, or ``None``.

    Args:
        frame: The dataset DataFrame.

    Returns:
        The detected column name, or ``None``.
    """
    for name in frame.columns:
        low = str(name).lower()
        if any(hint in low for hint in _DATE_HINTS):
            return str(name)
    return None


def _populated_mask(series: pd.Series) -> pd.Series:
    """Return a boolean mask marking rows where a field is populated.

    Treats both null and the empty string as "not populated" -- the two ways
    Socrata encodes a missing value.

    Args:
        series: One column of a dataset DataFrame.

    Returns:
        A boolean Series, ``True`` where the value is populated.
    """
    text = series.astype("string")
    return text.notna() & (text != "")


def _date_range(frame: pd.DataFrame, field: str, date_field: str | None) -> tuple[str, str] | None:
    """Bracket the populated rows of ``field`` by the dataset's date column.

    Args:
        frame: The dataset DataFrame.
        field: The probed field.
        date_field: The time-axis column to bracket by.

    Returns:
        A ``(earliest, latest)`` ISO date pair, or ``None`` when there is no
        usable date column or no populated rows.
    """
    if not date_field or date_field not in frame.columns:
        return None
    populated = frame.loc[_populated_mask(frame[field]), date_field]
    parsed = pd.to_datetime(populated, errors="coerce")
    earliest = parsed.min()
    latest = parsed.max()
    if pd.isna(earliest) or pd.isna(latest):
        return None
    return earliest.date().isoformat(), latest.date().isoformat()


def field_coverage(
    dataset_id: str,
    field: str,
    *,
    date_field: str | None = None,
) -> FieldCoverage:
    """Probe how one field is actually populated across a cached dataset.

    This is the defence against the recent-window trap: it reports the populated
    fraction and the populated date range, and states a warning when the pattern
    looks like a recent operational window rather than the dataset's full history.

    Args:
        dataset_id: Socrata four-by-four dataset identifier (must be cached).
        field: The field to probe, by its machine name (``columns_field_name``).
        date_field: The time-axis column to bracket the populated rows by.
            Auto-detected from the column names when omitted.

    Returns:
        A :class:`FieldCoverage` describing the field's actual population.

    Raises:
        FileNotFoundError: If the dataset is not cached.
        KeyError: If ``field`` is not a column of the dataset. The message lists
            the available fields and reminds the caller to use the machine field
            name, not the display name.
    """
    frame = _read_cached(dataset_id)
    if field not in frame.columns:
        available = ", ".join(str(c) for c in frame.columns)
        raise KeyError(
            f"field {field!r} is not a column of {dataset_id}. Available fields: "
            f"{available}. Query with columns_field_name (the machine name), not "
            "columns_name (the display name)."
        )

    populated = _populated_mask(frame[field])
    total_rows = len(frame)
    populated_rows = int(populated.sum())
    populated_pct = (populated_rows / total_rows * 100.0) if total_rows else 0.0

    if date_field is None:
        date_field = _primary_date_column(frame)
    dates = _date_range(frame, field, date_field)
    earliest_date, latest_date = dates if dates else (None, None)

    warning = ""
    if 0.0 < populated_pct < 99.0:
        warning = (
            f"field {field!r} is populated for only {populated_rows} of {total_rows} "
            f"rows ({populated_pct:.1f}%)."
        )
        if earliest_date and latest_date:
            warning += (
                f" The populated rows span {earliest_date} to {latest_date} -- this looks "
                "like a recent operational window, not the dataset's full history. Do not "
                "sum or rate over all rows; restrict to the populated window."
            )
        else:
            warning += (
                " Do not sum or rate over all rows -- the blank rows may mean "
                "'not tracked', not 'zero'."
            )

    return FieldCoverage(
        dataset_id=dataset_id,
        field=field,
        total_rows=total_rows,
        populated_rows=populated_rows,
        populated_pct=round(populated_pct, 2),
        date_field=date_field,
        earliest_date=earliest_date,
        latest_date=latest_date,
        warning=warning,
    )


def coverage_audit(
    dataset_id: str,
    *,
    threshold: float = 99.0,
    top: int = 10,
) -> list[FieldCoverage]:
    """Flag every field in a cached dataset that is only partly populated.

    An automated version of the field-population gotcha: instead of checking one
    field by hand, scan all of them and return the least-populated first. This
    is how a caller discovers, up front, that a "total" column is really a recent
    window.

    Args:
        dataset_id: Socrata four-by-four dataset identifier (must be cached).
        threshold: A field is flagged when its populated fraction is below this
            percentage (default ``99.0`` -- i.e. any field missing even a small
            slice is surfaced).
        top: Maximum number of fields to return, least-populated first.

    Returns:
        A list of :class:`FieldCoverage`, least-populated first, capped at
        ``top``. Empty when every field is fully populated.

    Raises:
        FileNotFoundError: If the dataset is not cached.
    """
    frame = _read_cached(dataset_id)
    date_field = _primary_date_column(frame)

    probes: list[FieldCoverage] = []
    for column in frame.columns:
        field_name = str(column)
        populated = _populated_mask(frame[column])
        total_rows = len(frame)
        populated_rows = int(populated.sum())
        populated_pct = (populated_rows / total_rows * 100.0) if total_rows else 0.0
        if populated_pct >= threshold:
            continue
        dates = _date_range(frame, field_name, date_field)
        probes.append(
            FieldCoverage(
                dataset_id=dataset_id,
                field=field_name,
                total_rows=total_rows,
                populated_rows=populated_rows,
                populated_pct=round(populated_pct, 2),
                date_field=date_field,
                earliest_date=dates[0] if dates else None,
                latest_date=dates[1] if dates else None,
                warning=(
                    f"populated for {populated_rows} of {total_rows} rows "
                    f"({populated_pct:.1f}%); treat any total/rate over this "
                    "field as windowed, not complete"
                ),
            )
        )

    probes.sort(key=lambda probe: probe.populated_pct)
    return probes[:top]


@dataclass(frozen=True)
class DatasetProfile:
    """A dataset's schema and coverage, for validating a query before running it.

    Attributes:
        dataset_id: The Socrata four-by-four dataset identifier.
        name: Human-readable dataset name.
        category: Catalog category, or empty string when unknown.
        tags: Catalog tags.
        columns_field_name: The machine field names -- the only names a query
            accepts. Querying with a display name returns zero rows silently.
        columns_datatype: Field types as reported by the catalog.
        columns_name: Display names (what a human reads; not what a query uses).
        update_frequency: How often the dataset is refreshed, if catalogued.
        data_updated_at: Last time the data was updated, if catalogued.
        cached: Whether the dataset's rows are cached locally (needed for the
            coverage fields below).
        row_count: Cached row count, or ``None`` when not cached.
        earliest_date: Cached data's earliest date, or ``None``.
        latest_date: Cached data's latest date, or ``None``.
        coverage_flags: Fields that are only partly populated (the recent-window
            traps), least-populated first.
    """

    dataset_id: str
    name: str
    category: str
    tags: tuple[str, ...]
    columns_field_name: tuple[str, ...]
    columns_datatype: tuple[str, ...]
    columns_name: tuple[str, ...]
    update_frequency: str
    data_updated_at: str
    cached: bool
    row_count: int | None
    earliest_date: str | None
    latest_date: str | None
    coverage_flags: tuple[FieldCoverage, ...] = ()


def dataset_profile(
    dataset_id: str,
    *,
    probe: bool = False,
    top: int = 10,
) -> DatasetProfile:
    """Build a schema-and-coverage profile for a dataset.

    The schema (field names, types, display names, update cadence) is read from
    the catalog cache -- instant, no network. When the dataset's rows are cached,
    the profile is enriched with row count, the dataset's own date range (the
    era-gap signal), and -- when ``probe`` is set -- the list of fields that are
    only partly populated.

    Args:
        dataset_id: Socrata four-by-four dataset identifier.
        probe: When True and the dataset is cached, include the
            :meth:`coverage_audit` flags in the profile.
        top: Cap on coverage flags when ``probe`` is set.

    Returns:
        A :class:`DatasetProfile`. ``row_count``, ``earliest_date``, and
        ``latest_date`` are ``None`` when the dataset is not cached.

    Raises:
        FileNotFoundError: If the catalog cache has never been refreshed.
    """
    entry = catalog.get(dataset_id)
    if entry is None:
        raise KeyError(
            f"dataset {dataset_id!r} is not in the catalog cache. Run refresh_catalog "
            "(or scripts/refresh_catalog.py) first, then retry."
        )

    cached_path = RAW_DIR / f"{dataset_id}.parquet"
    cached = cached_path.exists()
    row_count: int | None = None
    earliest_date: str | None = None
    latest_date: str | None = None
    coverage_flags: tuple[FieldCoverage, ...] = ()

    if cached:
        frame = pd.read_parquet(cached_path)
        row_count = len(frame)
        date_field = _primary_date_column(frame)
        if date_field:
            parsed = pd.to_datetime(frame[date_field], errors="coerce")
            earliest = parsed.min()
            latest = parsed.max()
            if not pd.isna(earliest):
                earliest_date = earliest.date().isoformat()
            if not pd.isna(latest):
                latest_date = latest.date().isoformat()
        if probe:
            coverage_flags = tuple(coverage_audit(dataset_id, threshold=99.0, top=top))

    return DatasetProfile(
        dataset_id=dataset_id,
        name=entry.get("name", ""),
        category=entry.get("category", ""),
        tags=tuple(entry.get("tags") or []),
        columns_field_name=tuple(entry.get("columns_field_name") or []),
        columns_datatype=tuple(entry.get("columns_datatype") or []),
        columns_name=tuple(entry.get("columns_name") or []),
        update_frequency=entry.get("update_frequency", ""),
        data_updated_at=entry.get("data_updated_at", ""),
        cached=cached,
        row_count=row_count,
        earliest_date=earliest_date,
        latest_date=latest_date,
        coverage_flags=coverage_flags,
    )
