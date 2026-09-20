from __future__ import annotations

import urllib.parse
import urllib.request
from pathlib import Path

from bike_scraper.models import Listing
from bike_scraper.sites.bikemaster import USER_AGENT


def cache_thumbnail(listing: Listing, thumbs_dir: Path) -> str | None:
    if not listing.image_url:
        return None
    suffix = Path(urllib.parse.urlparse(listing.image_url).path).suffix.lower() or ".jpg"
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        suffix = ".jpg"
    filename = f"{listing.site}-{listing.listing_id}{suffix}"
    dest = thumbs_dir / filename
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return f"thumbs/{filename}"
    request = urllib.request.Request(
        listing.image_url,
        headers={"User-Agent": USER_AGENT, "Accept": "image/*,*/*;q=0.8"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read()
    except OSError:
        return None
    if not data:
        return None
    dest.write_bytes(data)
    return f"thumbs/{filename}"
