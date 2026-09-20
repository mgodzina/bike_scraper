from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from bike_scraper.config import (
    load_config,
    resolve_db_path,
    resolve_last_run_path,
    resolve_report_path,
    resolve_thumbs_dir,
)
from bike_scraper.models import AppConfig, Listing, Search
from bike_scraper.report import format_price, write_report
from bike_scraper.sites import bikemaster, otomoto
from bike_scraper.store import Store
from bike_scraper.thumbs import cache_thumbnail

CATEGORY_LABELS = {
    "available": "available now",
    "upcoming": "upcoming",
    "otomoto": "otomoto",
}


@dataclass
class Finding:
    listing: Listing
    kind: str  # new | price_change | seen
    previous_price: int | None = None


@dataclass
class RunResult:
    text: str
    report_path: Path
    new_count: int
    total_count: int


def fetch_search(search: Search, delay_seconds: float) -> list[Listing]:
    if search.site == "bikemaster":
        return bikemaster.fetch_search(search.query, search.categories, delay_seconds)
    if search.site == "otomoto":
        return otomoto.fetch_search(search.url or search.query, delay_seconds)
    raise ValueError(f"Unsupported site: {search.site}")


def collect_findings(store: Store, listings: list[Listing]) -> list[Finding]:
    findings: list[Finding] = []
    for listing in listings:
        seen = store.get(listing.site, listing.listing_id)
        if seen is None:
            finding = Finding(listing=listing, kind="new")
        elif seen.price_pln != listing.price_pln:
            finding = Finding(listing=listing, kind="price_change", previous_price=seen.price_pln)
        else:
            finding = Finding(listing=listing, kind="seen")
        store.upsert(listing, kind=finding.kind, previous_price=finding.previous_price)
        findings.append(finding)
    return findings


def format_report(
    search: Search,
    listings: list[Listing],
    findings: list[Finding],
    first_run: bool,
    show_all: bool,
) -> str:
    interesting = [item for item in findings if item.kind in {"new", "price_change"}]
    if first_run and not show_all:
        lines = [
            f'{search.site} — first run for "{search.query}"',
            f"Saved {len(listings)} existing listing(s). They appear under New in the HTML report.",
        ]
        if listings:
            lines.append("")
            lines.extend(_listing_lines(listings))
        return "\n".join(lines)

    if show_all:
        header = f'{search.site} — {len(listings)} current match(es) for "{search.query}"'
        body = _listing_lines(listings) if listings else ["(none)"]
        extras = [item for item in interesting if not first_run]
        if extras:
            body.extend(["", "Changes this run:", *_finding_lines(extras)])
        return "\n".join([header, "", *body])

    if not interesting:
        return f'{search.site} — no new matches for "{search.query}" (watching {len(listings)})'

    lines = [f'{search.site} — {len(interesting)} update(s) for "{search.query}"', ""]
    lines.extend(_finding_lines(interesting))
    return "\n".join(lines)


def _listing_lines(listings: list[Listing]) -> list[str]:
    return _finding_lines([Finding(listing=item, kind="seen") for item in listings])


def _finding_lines(findings: list[Finding]) -> list[str]:
    lines: list[str] = []
    for item in findings:
        listing = item.listing
        label = CATEGORY_LABELS.get(listing.category, listing.category)
        price = format_price(listing.price_pln)
        if listing.old_price_pln and listing.old_price_pln != listing.price_pln:
            price = f"{price} (was {format_price(listing.old_price_pln)})"
        if item.kind == "price_change":
            header = f"PRICE · {label} · previously {format_price(item.previous_price)}"
        elif item.kind == "new":
            header = f"NEW · {label}"
        else:
            header = label
        lines.append(header)
        lines.append(listing.title)
        lines.append(price)
        lines.append(listing.url)
        if listing.snippet:
            lines.append(listing.snippet)
        lines.append("")
    return lines[:-1] if lines and lines[-1] == "" else lines


def _cache_thumbs(store: Store, listings: list[Listing], thumbs_dir: Path) -> None:
    for listing in listings:
        image_file = cache_thumbnail(listing, thumbs_dir)
        if image_file:
            store.set_image_file(listing.site, listing.listing_id, image_file)


def write_current_report(config: AppConfig, config_path: Path | None = None) -> Path:
    store = Store(resolve_db_path(config, config_path))
    try:
        return write_report(resolve_report_path(config, config_path), store.list_all())
    finally:
        store.close()


def last_run_path(config_path: Path | None = None) -> Path:
    return resolve_last_run_path(load_config(config_path), config_path)


def already_ran_today(config_path: Path | None = None) -> bool:
    path = last_run_path(config_path)
    if not path.exists():
        return False
    return path.read_text(encoding="utf-8").strip() == date.today().isoformat()


def mark_ran_today(config_path: Path | None = None) -> None:
    path = last_run_path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(date.today().isoformat() + "\n", encoding="utf-8")


def reset_data(config_path: Path | None = None) -> Path:
    config = load_config(config_path)
    db_path = resolve_db_path(config, config_path)
    thumbs_dir = resolve_thumbs_dir(config, config_path)
    stamp = resolve_last_run_path(config, config_path)
    if db_path.exists():
        db_path.unlink()
    if stamp.exists():
        stamp.unlink()
    if thumbs_dir.exists():
        shutil.rmtree(thumbs_dir)
    return write_current_report(config, config_path)


def run(
    config_path: Path | None = None,
    show_all: bool = False,
    query_override: str | None = None,
) -> RunResult:
    config: AppConfig = load_config(config_path)
    store = Store(resolve_db_path(config, config_path))
    first_run = store.is_empty()
    store.begin_run()
    sections: list[str] = []
    new_count = 0
    try:
        for search in config.searches:
            if query_override and search.site != "otomoto":
                search = Search(
                    site=search.site,
                    query=query_override,
                    categories=search.categories,
                    url=search.url,
                )
            listings = fetch_search(search, config.request_delay_seconds)
            findings = collect_findings(store, listings)
            _cache_thumbs(store, listings, resolve_thumbs_dir(config, config_path))
            new_count += sum(1 for item in findings if item.kind in {"new", "price_change"})
            sections.append(
                format_report(search, listings, findings, first_run=first_run, show_all=show_all)
            )
        report_path = write_report(resolve_report_path(config, config_path), store.list_all())
        total_count = len(store.list_all())
    finally:
        store.close()
    text = "\n\n".join(sections)
    text += f"\n\nHTML report: {report_path}"
    mark_ran_today(config_path)
    return RunResult(text=text, report_path=report_path, new_count=new_count, total_count=total_count)
