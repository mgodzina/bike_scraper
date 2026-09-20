from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from bike_scraper.models import Listing

_NEW_COLUMNS = (
    ("old_price_pln", "INTEGER"),
    ("previous_price", "INTEGER"),
    ("snippet", "TEXT"),
    ("image_url", "TEXT"),
    ("image_file", "TEXT"),
    ("last_change", "TEXT"),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class StoredListing:
    site: str
    listing_id: str
    url: str
    title: str
    category: str
    price_pln: int | None
    old_price_pln: int | None
    previous_price: int | None
    snippet: str
    image_url: str | None
    image_file: str | None
    first_seen: str
    last_seen: str
    last_change: str


class Store:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS listings (
                site TEXT NOT NULL,
                listing_id TEXT NOT NULL,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                price_pln INTEGER,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                PRIMARY KEY (site, listing_id)
            )
            """
        )
        self._migrate()
        self._conn.commit()

    def _migrate(self) -> None:
        existing = {
            row["name"] for row in self._conn.execute("PRAGMA table_info(listings)")
        }
        for name, decl in _NEW_COLUMNS:
            if name not in existing:
                self._conn.execute(f"ALTER TABLE listings ADD COLUMN {name} {decl}")

    def close(self) -> None:
        self._conn.close()

    def is_empty(self) -> bool:
        row = self._conn.execute("SELECT COUNT(*) AS n FROM listings").fetchone()
        return int(row["n"]) == 0

    def begin_run(self) -> str:
        self._conn.execute("UPDATE listings SET last_change = ''")
        self._conn.commit()
        return _now()

    def get(self, site: str, listing_id: str) -> StoredListing | None:
        row = self._conn.execute(
            "SELECT * FROM listings WHERE site = ? AND listing_id = ?",
            (site, listing_id),
        ).fetchone()
        return _row_to_listing(row) if row is not None else None

    def list_all(self) -> list[StoredListing]:
        rows = self._conn.execute(
            """
            SELECT * FROM listings
            ORDER BY
                CASE last_change WHEN 'new' THEN 0 WHEN 'price_change' THEN 1 ELSE 2 END,
                last_seen DESC,
                title COLLATE NOCASE
            """
        ).fetchall()
        return [_row_to_listing(row) for row in rows]

    def upsert(self, listing: Listing, *, kind: str, previous_price: int | None) -> None:
        now = _now()
        last_change = kind if kind in {"new", "price_change"} else ""
        self._conn.execute(
            """
            INSERT INTO listings (
                site, listing_id, url, title, category, price_pln, old_price_pln,
                previous_price, snippet, image_url, image_file, first_seen, last_seen, last_change
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(site, listing_id) DO UPDATE SET
                url = excluded.url,
                title = excluded.title,
                category = excluded.category,
                price_pln = excluded.price_pln,
                old_price_pln = excluded.old_price_pln,
                previous_price = excluded.previous_price,
                snippet = excluded.snippet,
                image_url = COALESCE(excluded.image_url, listings.image_url),
                image_file = COALESCE(excluded.image_file, listings.image_file),
                last_seen = excluded.last_seen,
                last_change = excluded.last_change
            """,
            (
                listing.site,
                listing.listing_id,
                listing.url,
                listing.title,
                listing.category,
                listing.price_pln,
                listing.old_price_pln,
                previous_price,
                listing.snippet,
                listing.image_url,
                None,
                now,
                now,
                last_change,
            ),
        )
        self._conn.commit()

    def set_image_file(self, site: str, listing_id: str, image_file: str) -> None:
        self._conn.execute(
            "UPDATE listings SET image_file = ? WHERE site = ? AND listing_id = ?",
            (image_file, site, listing_id),
        )
        self._conn.commit()


def _row_to_listing(row: sqlite3.Row) -> StoredListing:
    keys = row.keys()
    return StoredListing(
        site=row["site"],
        listing_id=row["listing_id"],
        url=row["url"],
        title=row["title"],
        category=row["category"],
        price_pln=row["price_pln"],
        old_price_pln=row["old_price_pln"] if "old_price_pln" in keys else None,
        previous_price=row["previous_price"] if "previous_price" in keys else None,
        snippet=row["snippet"] or "" if "snippet" in keys else "",
        image_url=row["image_url"] if "image_url" in keys else None,
        image_file=row["image_file"] if "image_file" in keys else None,
        first_seen=row["first_seen"],
        last_seen=row["last_seen"],
        last_change=row["last_change"] or "" if "last_change" in keys else "",
    )
