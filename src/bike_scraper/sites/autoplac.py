from __future__ import annotations

import http.cookiejar
import json
import re
import urllib.parse
import urllib.request

from bike_scraper.models import Listing

SITE = "autoplac"
BASE = "https://autoplac.pl"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
NG_STATE_RE = re.compile(r'<script id="ng-state" type="application/json">(.*?)</script>', re.S)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _search_body(html: str) -> dict:
    match = NG_STATE_RE.search(html)
    if match is None:
        raise RuntimeError("Autoplac page did not include listing data (possible bot check).")
    payload = json.loads(match.group(1))
    if not isinstance(payload, dict):
        raise RuntimeError("Autoplac listing data was present but had an unexpected shape.")
    for key, entry in payload.items():
        if "/offers/search" not in str(key):
            continue
        body = entry.get("body") if isinstance(entry, dict) else None
        if isinstance(body, dict) and "offerList" in body:
            return body
    raise RuntimeError("Autoplac listing data was present but had no search results block.")


def _absolute_url(path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return urllib.parse.urljoin(BASE, path)


def _price(offer: dict) -> tuple[int | None, int | None]:
    info = offer.get("priceInfo") or {}
    primary = info.get("primary") or {}
    price = primary.get("price")
    old = primary.get("promoPriceValue") or info.get("promoValue")
    try:
        price_pln = int(price) if price not in (None, "") else None
    except (TypeError, ValueError):
        price_pln = None
    try:
        old_pln = int(old) if old not in (None, "") else None
    except (TypeError, ValueError):
        old_pln = None
    return price_pln, old_pln


def _image(item: dict) -> str | None:
    photos = item.get("photoList") or []
    if not photos or not isinstance(photos[0], dict):
        return None
    photo = photos[0]
    for key in ("miniatureUrl", "webpMiniatureUrl", "url", "webpUrl"):
        value = photo.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _parse_item(item: dict) -> Listing | None:
    offer = item.get("offer") or {}
    listing_id = str(offer.get("id") or "").strip()
    path = str(offer.get("webUrl") or "").strip()
    title = _clean(str(offer.get("title") or ""))
    if not listing_id or not path or not title:
        return None
    year = offer.get("productionYear")
    mileage = offer.get("mileage")
    capacity = offer.get("engineCapacity")
    city = offer.get("city") or ""
    region = offer.get("voivodeshipDisplay") or offer.get("voivodeship") or ""
    place = ", ".join(part for part in (city, region) if part)
    bits = []
    if year:
        bits.append(str(year))
    if mileage not in (None, ""):
        bits.append(f"{int(mileage):,} km".replace(",", " "))
    if capacity not in (None, ""):
        bits.append(f"{capacity} cm3")
    if place:
        bits.append(place)
    snippet = " · ".join(bits)
    price, old_price = _price(offer)
    return Listing(
        site=SITE,
        listing_id=listing_id,
        url=_absolute_url(path),
        title=title,
        category=SITE,
        price_pln=price,
        old_price_pln=old_price,
        snippet=snippet,
        image_url=_image(item),
    )


def parse_listings(html: str) -> list[Listing]:
    body = _search_body(html)
    listings: list[Listing] = []
    seen: set[str] = set()
    for item in body.get("offerList") or []:
        listing = _parse_item(item or {})
        if listing is None or listing.listing_id in seen:
            continue
        seen.add(listing.listing_id)
        listings.append(listing)
    return listings


def fetch(url: str, timeout: float = 30) -> str:
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )
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
        raise RuntimeError(f"Autoplac returned HTTP {status} for {url}")
    return raw.decode(encoding, errors="replace")


def fetch_search(url: str, delay_seconds: float = 1.5) -> list[Listing]:
    if not url:
        raise ValueError("Autoplac search needs a full search URL")
    return parse_listings(fetch(url))
