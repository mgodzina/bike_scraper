from __future__ import annotations

import http.cookiejar
import json
import re
import time
import urllib.parse
import urllib.request

from bike_scraper.models import Listing

SITE = "otomoto"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
MAX_PAGES = 20
NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def with_page(url: str, page: int) -> str:
    parts = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qs(parts.query, keep_blank_values=True)
    if page <= 1:
        query.pop("page", None)
    else:
        query["page"] = [str(page)]
    return urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urllib.parse.urlencode(query, doseq=True), parts.fragment)
    )


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _advert_search(html: str) -> dict:
    match = NEXT_DATA_RE.search(html)
    if match is None:
        raise RuntimeError("Otomoto page did not include listing data (possible bot check).")
    payload = json.loads(match.group(1))
    urql = payload.get("props", {}).get("pageProps", {}).get("urqlState") or {}
    for entry in urql.values():
        raw = entry.get("data") if isinstance(entry, dict) else None
        if not raw:
            continue
        data = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(data, dict) and "advertSearch" in data:
            return data["advertSearch"]
    raise RuntimeError("Otomoto listing data was present but had no search results block.")


def _price(node: dict) -> int | None:
    amount = (node.get("price") or {}).get("amount") or {}
    for key in ("units", "value"):
        value = amount.get(key)
        if value in (None, ""):
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _old_price(node: dict) -> int | None:
    drop = node.get("priceDrop") or {}
    if not isinstance(drop, dict):
        return None
    for key in ("previousPrice", "oldPrice", "price"):
        candidate = drop.get(key)
        if isinstance(candidate, dict):
            value = (candidate.get("amount") or candidate).get("units") or candidate.get("value")
        else:
            value = candidate
        if value in (None, ""):
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _params(node: dict) -> dict[str, str]:
    values: dict[str, str] = {}
    for item in node.get("parameters") or []:
        key = item.get("key")
        if not key:
            continue
        values[key] = item.get("displayValue") or item.get("value") or ""
    return values


def parse_listings(html: str) -> tuple[list[Listing], int, int, int]:
    search = _advert_search(html)
    page_info = search.get("pageInfo") or {}
    listings = []
    for edge in search.get("edges") or []:
        node = (edge or {}).get("node") or {}
        listing = _parse_node(node)
        if listing is not None:
            listings.append(listing)
    total = int(search.get("totalCount") or 0)
    page_size = int(page_info.get("pageSize") or len(listings) or 32)
    offset = int(page_info.get("currentOffset") or 0)
    return listings, total, page_size, offset


def _parse_node(node: dict) -> Listing | None:
    listing_id = str(node.get("id") or "").strip()
    url = str(node.get("url") or "").strip()
    title = _clean(str(node.get("title") or ""))
    if not listing_id or not url or not title:
        return None
    params = _params(node)
    location = node.get("location") or {}
    city = ((location.get("city") or {}).get("name")) or ""
    region = ((location.get("region") or {}).get("name")) or ""
    place = ", ".join(part for part in (city, region) if part)
    bits = [params.get("year"), params.get("mileage"), params.get("engine_capacity"), place]
    snippet = " · ".join(bit for bit in bits if bit)
    description = _clean(str(node.get("shortDescription") or ""))
    if description:
        snippet = f"{snippet} — {description}" if snippet else description
    thumbnail = node.get("thumbnail") or {}
    image = thumbnail.get("x1") or thumbnail.get("x2")
    return Listing(
        site=SITE,
        listing_id=listing_id,
        url=url,
        title=title,
        category=SITE,
        price_pln=_price(node),
        old_price_pln=_old_price(node),
        snippet=snippet,
        image_url=image if isinstance(image, str) else None,
    )


def fetch(url: str, opener: urllib.request.OpenerDirector, timeout: float = 30) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
        },
    )
    with opener.open(request, timeout=timeout) as response:
        raw = response.read()
        encoding = response.headers.get_content_charset() or "utf-8"
        status = getattr(response, "status", None) or response.getcode()
    if status and status >= 400:
        raise RuntimeError(f"Otomoto returned HTTP {status} for {url}")
    return raw.decode(encoding, errors="replace")


def fetch_search(url: str, delay_seconds: float = 1.5) -> list[Listing]:
    if not url:
        raise ValueError("Otomoto search needs a full search URL")
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )
    listings: list[Listing] = []
    seen_ids: set[str] = set()
    page = 1
    while page <= MAX_PAGES:
        if page > 1:
            time.sleep(delay_seconds)
        html = fetch(with_page(url, page), opener)
        page_listings, total, page_size, offset = parse_listings(html)
        for listing in page_listings:
            if listing.listing_id in seen_ids:
                continue
            seen_ids.add(listing.listing_id)
            listings.append(listing)
        next_offset = offset + max(page_size, 1)
        if not page_listings or next_offset >= total:
            break
        page += 1
    return listings
