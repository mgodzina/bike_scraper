from __future__ import annotations

import re
import time
import urllib.parse
import urllib.request
from collections.abc import Iterable

from bs4 import BeautifulSoup, Tag

from bike_scraper.models import Listing

SITE = "bikemaster"
BASE = "https://bikemaster.pl"
CATEGORIES = {
    "available": "dostepny-teraz",
    "upcoming": "dostepny-wkrotce",
}
CATEGORY_LABELS = {
    "available": "available now",
    "upcoming": "upcoming",
}

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
POST_ID_RE = re.compile(r"(?:^|\s)post-(\d+)(?:\s|$)")
PRICE_RE = re.compile(r"(\d[\d\s\u00a0.]*)\s*zł", re.IGNORECASE)


def search_url(category: str, query: str, page: int = 1) -> str:
    slug = CATEGORIES[category]
    path = f"/dostepny/{slug}/" if page <= 1 else f"/dostepny/{slug}/page/{page}/"
    return f"{BASE}{path}?s={urllib.parse.quote(query)}"


def parse_pln(text: str) -> int | None:
    match = PRICE_RE.search(text.replace("\xa0", " "))
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group(1))
    return int(digits) if digits else None


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_listings(html: str, category: str) -> list[Listing]:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("#archive-container .custom-archive-loop-item")
    listings: list[Listing] = []
    for card in cards:
        listing = _parse_card(card, category)
        if listing is not None:
            listings.append(listing)
    return listings


def next_page_url(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    link = soup.select_one("a.next.page-numbers")
    if link is None:
        return None
    href = link.get("href")
    if not isinstance(href, str) or not href:
        return None
    return urllib.parse.urljoin(BASE, href)


def _parse_card(card: Tag, category: str) -> Listing | None:
    classes = " ".join(card.get("class") or [])
    match = POST_ID_RE.search(classes)
    if match is None:
        return None

    heading = card.select_one("h2")
    if heading is None:
        return None
    title = _clean(heading.get_text(" ", strip=True))
    if not title:
        return None

    url = _card_url(card, heading)
    if url is None:
        return None

    prices = [parsed for h3 in card.select("h3") if (parsed := parse_pln(h3.get_text())) is not None]
    if len(prices) >= 2:
        old_price, price = prices[0], prices[1]
    elif prices:
        old_price, price = None, prices[0]
    else:
        old_price, price = None, None

    paragraph = card.select_one("p")
    snippet = _clean(paragraph.get_text(" ", strip=True)) if paragraph else ""
    if len(snippet) > 280:
        snippet = snippet[:277].rstrip() + "..."

    return Listing(
        site=SITE,
        listing_id=match.group(1),
        url=url,
        title=title,
        category=category,
        price_pln=price,
        old_price_pln=old_price,
        snippet=snippet,
        image_url=_card_image(card),
    )


def _card_image(card: Tag) -> str | None:
    img = card.select_one("figure img") or card.select_one("img")
    if img is None:
        return None
    srcset = img.get("srcset")
    if isinstance(srcset, str) and srcset.strip():
        candidates: list[tuple[int, str]] = []
        for item in srcset.split(","):
            piece = item.strip()
            if not piece:
                continue
            url, _, size = piece.rpartition(" ")
            if url and size.endswith("w"):
                try:
                    width = int(size[:-1])
                except ValueError:
                    continue
                candidates.append((width, url))
        if candidates:
            candidates.sort(key=lambda item: abs(item[0] - 400))
            return candidates[0][1]
    src = img.get("src")
    return src if isinstance(src, str) and src else None


def _card_url(card: Tag, heading: Tag) -> str | None:
    for candidate in (
        heading.find_parent("a"),
        card.select_one("a.kb-advanced-heading-link"),
        card.select_one("a.kb-section-link-overlay"),
        heading.find("a"),
    ):
        if candidate is None:
            continue
        href = candidate.get("href")
        if isinstance(href, str) and href:
            return href.split("?")[0].rstrip("/") + "/"
    return None


def fetch(url: str, timeout: float = 30) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
        encoding = response.headers.get_content_charset() or "utf-8"
    return raw.decode(encoding, errors="replace")


def fetch_search(
    query: str,
    categories: Iterable[str],
    delay_seconds: float = 1.5,
) -> list[Listing]:
    listings: list[Listing] = []
    first_request = True
    for category in categories:
        if category not in CATEGORIES:
            raise ValueError(f"Unknown Bikemaster category: {category}")
        url: str | None = search_url(category, query)
        page = 1
        while url:
            if not first_request:
                time.sleep(delay_seconds)
            first_request = False
            html = fetch(url)
            listings.extend(parse_listings(html, category))
            url = next_page_url(html)
            page += 1
            if page > 20:
                break
    return listings
