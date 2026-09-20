from __future__ import annotations

import tomllib
from pathlib import Path

from bike_scraper.models import AppConfig, Search

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config.toml"


def _parse_search(item: dict) -> Search:
    site = item["site"]
    categories = item.get("categories")
    if not categories:
        categories = ("available", "upcoming") if site == "bikemaster" else ()
    return Search(
        site=site,
        query=item.get("query") or item.get("url") or site,
        categories=tuple(categories),
        url=item.get("url"),
    )


def load_config(path: Path | None = None) -> AppConfig:
    config_path = path or DEFAULT_CONFIG
    with config_path.open("rb") as fh:
        raw = tomllib.load(fh)

    searches = tuple(_parse_search(item) for item in raw["searches"])
    return AppConfig(
        database=str(raw.get("database") or "data/seen.db"),
        report=str(raw.get("report") or "data/report.html"),
        thumbs=str(raw.get("thumbs") or "data/thumbs"),
        request_delay_seconds=float(raw.get("request_delay_seconds") or 1.5),
        searches=searches,
    )


def _resolve(path_value: str, config_path: Path | None = None) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    base = (config_path or DEFAULT_CONFIG).parent
    return (base / path).resolve()


def resolve_db_path(config: AppConfig, config_path: Path | None = None) -> Path:
    return _resolve(config.database, config_path)


def resolve_report_path(config: AppConfig, config_path: Path | None = None) -> Path:
    return _resolve(config.report, config_path)


def resolve_thumbs_dir(config: AppConfig, config_path: Path | None = None) -> Path:
    return _resolve(config.thumbs, config_path)


def resolve_last_run_path(config: AppConfig, config_path: Path | None = None) -> Path:
    return resolve_db_path(config, config_path).with_name("last_run")
