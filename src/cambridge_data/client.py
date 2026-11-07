"""Client for the Socrata SODA API (data.cambridgema.gov resource endpoints)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import requests

from cambridge_data.config import PORTAL_DOMAIN, load_credentials

_PAGE_SIZE = 50_000  # Socrata's practical max page size for $limit/$offset paging
_TIMEOUT = 60


class SodaClient:
    """Thin wrapper over the Socrata SODA API for a single domain.

    Handles auth headers, SoQL query params, and offset-based pagination.
    Does not infer types -- Socrata returns every column as a JSON string;
    callers coerce types downstream (e.g. in scripts/fetch_dataset.py).
    """

    def __init__(self, domain: str = PORTAL_DOMAIN) -> None:
        """Initialize the client.

        Args:
            domain: Socrata portal domain to query.
        """
        self._base_url = f"https://{domain}/resource"
        creds = load_credentials()
        self._session = requests.Session()
        self._session.headers.update(creds.headers)
        if creds.basic_auth:
            self._session.auth = creds.basic_auth

    def query(
        self,
        dataset_id: str,
        *,
        select: str | None = None,
        where: str | None = None,
        order: str | None = None,
        group: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Run a single SoQL query page against a dataset.

        Args:
            dataset_id: Socrata four-by-four dataset identifier (e.g. "ixg8-tyau").
            select: SoQL $select clause.
            where: SoQL $where clause.
            order: SoQL $order clause.
            group: SoQL $group clause.
            limit: SoQL $limit clause (row cap for this page).
            offset: SoQL $offset clause.

        Returns:
            List of row dicts as returned by the API.

        Raises:
            requests.HTTPError: On a non-2xx response.
        """
        params: dict[str, Any] = {"$offset": offset}
        if select:
            params["$select"] = select
        if where:
            params["$where"] = where
        if order:
            params["$order"] = order
        if group:
            params["$group"] = group
        if limit is not None:
            params["$limit"] = limit
        response = self._session.get(
            f"{self._base_url}/{dataset_id}.json", params=params, timeout=_TIMEOUT
        )
        response.raise_for_status()
        return response.json()

    def iter_all_rows(
        self,
        dataset_id: str,
        *,
        select: str | None = None,
        where: str | None = None,
        order: str | None = None,
        page_size: int = _PAGE_SIZE,
    ) -> Iterator[dict[str, Any]]:
        """Paginate through every row of a dataset (optionally filtered).

        Args:
            dataset_id: Socrata four-by-four dataset identifier.
            select: SoQL $select clause.
            where: SoQL $where clause.
            order: SoQL $order clause. Defaults to ":id" for stable paging.
            page_size: Rows requested per page.

        Yields:
            Row dicts, one per record, across all pages.
        """
        offset = 0
        effective_order = order or ":id"
        while True:
            page = self.query(
                dataset_id,
                select=select,
                where=where,
                order=effective_order,
                limit=page_size,
                offset=offset,
            )
            if not page:
                return
            yield from page
            if len(page) < page_size:
                return
            offset += page_size
