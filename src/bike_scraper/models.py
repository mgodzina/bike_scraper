from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Listing:
    site: str
    listing_id: str
    url: str
    title: str
    category: str
    price_pln: int | None
    old_price_pln: int | None
    snippet: str
    image_url: str | None = None


@dataclass(frozen=True)
class Search:
    site: str
    query: str
    categories: tuple[str, ...]
    url: str | None = None


@dataclass
class AppConfig:
    database: str
    report: str
    thumbs: str
    request_delay_seconds: float
    searches: tuple[Search, ...]
