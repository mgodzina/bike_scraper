from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path

from bike_scraper.store import StoredListing

CATEGORY_LABELS = {
    "available": "Available now",
    "upcoming": "Upcoming",
    "otomoto": "Otomoto",
}

SITE_LABELS = {
    "bikemaster": "Bikemaster",
    "otomoto": "Otomoto",
}


def format_price(value: int | None) -> str:
    if value is None:
        return "Price unknown"
    return f"{value:,} zł".replace(",", " ")


def write_report(path: Path, listings: list[StoredListing]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(listings), encoding="utf-8")
    return path


def render_report(listings: list[StoredListing]) -> str:
    new_items = [item for item in listings if item.last_change in {"new", "price_change"}]
    generated = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Bike watcher</title>
  <style>
    :root {{
      --bg: #f3efe6;
      --ink: #1b1a17;
      --muted: #5f5a52;
      --card: #fffdf8;
      --line: #d8d0c4;
      --accent: #b42318;
      --good: #13612e;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--ink);
    }}
    header {{
      padding: 1.25rem 1.5rem;
      border-bottom: 1px solid var(--line);
      background: #fffdf8;
    }}
    h1 {{
      margin: 0;
      font-size: 1.35rem;
      letter-spacing: 0.02em;
    }}
    .meta {{ color: var(--muted); font-size: 0.9rem; margin-top: 0.25rem; }}
    .tabs {{
      display: flex;
      gap: 0;
      padding: 0 1.5rem;
      margin-top: 1rem;
    }}
    .tabs button {{
      font: inherit;
      cursor: pointer;
      background: transparent;
      color: var(--ink);
      border: 1px solid var(--line);
      border-bottom: none;
      padding: 0.55rem 0.9rem;
    }}
    .tabs button.active {{
      background: var(--card);
      font-weight: 650;
    }}
    main {{ padding: 0 1.5rem 2rem; }}
    .panel {{
      display: none;
      background: var(--card);
      border: 1px solid var(--line);
      padding: 1rem;
      min-height: 12rem;
    }}
    .panel.active {{ display: block; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 1rem;
    }}
    article {{
      display: flex;
      flex-direction: column;
      border: 1px solid var(--line);
      background: #fff;
      min-height: 100%;
    }}
    article a.thumb {{
      display: block;
      aspect-ratio: 4 / 3;
      background: #ece7dc;
      overflow: hidden;
    }}
    article img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
    }}
    .body {{ padding: 0.85rem 0.95rem 1rem; display: flex; flex-direction: column; gap: 0.4rem; flex: 1; }}
    .badges {{ display: flex; flex-wrap: wrap; gap: 0.35rem; }}
    .badge {{
      font-size: 0.72rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      border: 1px solid var(--line);
      padding: 0.15rem 0.4rem;
      color: var(--muted);
    }}
    .badge.new {{ border-color: var(--good); color: var(--good); }}
    .badge.price {{ border-color: var(--accent); color: var(--accent); }}
    h2 {{
      margin: 0;
      font-size: 1.02rem;
      line-height: 1.3;
    }}
    .price {{ font-size: 1.15rem; font-weight: 700; }}
    .old {{ color: var(--muted); text-decoration: line-through; font-weight: 400; margin-left: 0.35rem; }}
    .snippet {{ color: var(--muted); font-size: 0.9rem; }}
    .open {{
      margin-top: auto;
      color: var(--accent);
      font-weight: 650;
      text-decoration: none;
    }}
    .open:hover {{ text-decoration: underline; }}
    .empty {{ color: var(--muted); padding: 1.5rem 0.5rem; }}
    .fav {{
      display: flex;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.9rem;
      color: var(--muted);
      cursor: pointer;
    }}
    .fav input {{ width: 1rem; height: 1rem; accent-color: var(--accent); }}
    footer {{ padding: 0 1.5rem 2rem; color: var(--muted); font-size: 0.85rem; }}
  </style>
</head>
<body>
  <header>
    <h1>Bike watcher</h1>
    <div class="meta">Updated {html.escape(generated)} · {len(new_items)} new · {len(listings)} saved</div>
  </header>
  <div class="tabs" role="tablist">
    <button type="button" class="active" data-tab="new" role="tab">New ({len(new_items)})</button>
    <button type="button" data-tab="all" role="tab">All ({len(listings)})</button>
    <button type="button" data-tab="favorites" role="tab">Favorites (0)</button>
  </div>
  <main>
    <section id="new" class="panel active">{_render_grid(new_items, empty="No new listings.")}</section>
    <section id="all" class="panel">{_render_grid(listings, empty="Database is empty.")}</section>
    <section id="favorites" class="panel"><p class="empty">No favorites yet.</p></section>
  </main>
  <footer>
    This is a static file. Run <code>python -m bike_scraper</code> to refresh it.
    Favorites are stored in this browser only. Delete <code>data/seen.db</code> to start over.
  </footer>
  <script>
    const STORAGE_KEY = "bike-watcher-favorites";
    const emptyFavorites = '<p class="empty">No favorites yet.</p>';

    function loadFavorites() {{
      try {{
        const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
        return new Set(Array.isArray(raw) ? raw : []);
      }} catch (error) {{
        return new Set();
      }}
    }}

    function saveFavorites(favorites) {{
      localStorage.setItem(STORAGE_KEY, JSON.stringify([...favorites]));
    }}

    function applyCheckboxes(favorites) {{
      document.querySelectorAll("article[data-listing-key]").forEach((card) => {{
        const box = card.querySelector("input.fav-box");
        if (box) box.checked = favorites.has(card.dataset.listingKey);
      }});
    }}

    function renderFavorites() {{
      const favorites = loadFavorites();
      const panel = document.getElementById("favorites");
      const tab = document.querySelector('[data-tab="favorites"]');
      const cards = [...document.querySelectorAll("#all article[data-listing-key]")]
        .filter((card) => favorites.has(card.dataset.listingKey));
      tab.textContent = `Favorites (${{cards.length}})`;
      if (!cards.length) {{
        panel.innerHTML = emptyFavorites;
        return;
      }}
      const grid = document.createElement("div");
      grid.className = "grid";
      cards.forEach((card) => grid.appendChild(card.cloneNode(true)));
      panel.replaceChildren(grid);
      applyCheckboxes(favorites);
    }}

    document.querySelectorAll(".tabs button").forEach((button) => {{
      button.addEventListener("click", () => {{
        document.querySelectorAll(".tabs button").forEach((item) => item.classList.remove("active"));
        document.querySelectorAll(".panel").forEach((item) => item.classList.remove("active"));
        button.classList.add("active");
        document.getElementById(button.dataset.tab).classList.add("active");
      }});
    }});
    document.addEventListener("change", (event) => {{
      if (!event.target.classList.contains("fav-box")) return;
      const card = event.target.closest("article[data-listing-key]");
      if (!card) return;
      const favorites = loadFavorites();
      if (event.target.checked) favorites.add(card.dataset.listingKey);
      else favorites.delete(card.dataset.listingKey);
      saveFavorites(favorites);
      applyCheckboxes(favorites);
      renderFavorites();
    }});
    applyCheckboxes(loadFavorites());
    renderFavorites();
  </script>
</body>
</html>
"""


def _render_grid(listings: list[StoredListing], *, empty: str) -> str:
    if not listings:
        return f'<p class="empty">{html.escape(empty)}</p>'
    cards = "\n".join(_render_card(item) for item in listings)
    return f'<div class="grid">{cards}</div>'


def _render_card(item: StoredListing) -> str:
    site_label = SITE_LABELS.get(item.site, item.site)
    label = CATEGORY_LABELS.get(item.category, item.category)
    badges = [f'<span class="badge">{html.escape(site_label)}</span>']
    if label and label.lower() != site_label.lower():
        badges.append(f'<span class="badge">{html.escape(label)}</span>')
    if item.last_change == "new":
        badges.append('<span class="badge new">New</span>')
    elif item.last_change == "price_change":
        badges.append('<span class="badge price">Price change</span>')
    old = ""
    if item.old_price_pln and item.old_price_pln != item.price_pln:
        old = f'<span class="old">{html.escape(format_price(item.old_price_pln))}</span>'
    elif item.previous_price and item.previous_price != item.price_pln:
        old = f'<span class="old">{html.escape(format_price(item.previous_price))}</span>'
    image = item.image_file or item.image_url or ""
    if image:
        thumb = (
            f'<a class="thumb" href="{html.escape(item.url, quote=True)}" target="_blank" rel="noopener noreferrer">'
            f'<img src="{html.escape(image, quote=True)}" alt=""></a>'
        )
    else:
        thumb = (
            f'<a class="thumb" href="{html.escape(item.url, quote=True)}" target="_blank" rel="noopener noreferrer"></a>'
        )
    snippet = f'<p class="snippet">{html.escape(item.snippet)}</p>' if item.snippet else ""
    key = html.escape(f"{item.site}:{item.listing_id}", quote=True)
    return f"""
    <article data-listing-key="{key}">
      {thumb}
      <div class="body">
        <div class="badges">{"".join(badges)}</div>
        <h2>{html.escape(item.title)}</h2>
        <div class="price">{html.escape(format_price(item.price_pln))}{old}</div>
        {snippet}
        <label class="fav"><input class="fav-box" type="checkbox"> Favorite</label>
        <a class="open" href="{html.escape(item.url, quote=True)}" target="_blank" rel="noopener noreferrer">Open listing</a>
      </div>
    </article>
    """
