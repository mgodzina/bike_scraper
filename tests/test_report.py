from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from bike_scraper.report import render_report
from bike_scraper.store import Store, StoredListing


def sample(last_change: str = "new") -> StoredListing:
    return StoredListing(
        site="bikemaster",
        listing_id="65159",
        url="https://bikemaster.pl/motocykle/mv-agusta-brutale-910/",
        title="MV AGUSTA BRUTALE 910",
        category="available",
        price_pln=16900,
        old_price_pln=19900,
        previous_price=None,
        snippet="Nice bike",
        image_url="https://example.com/bike.jpg",
        image_file="thumbs/bikemaster-65159.jpg",
        first_seen="2026-09-13T06:00:00+00:00",
        last_seen="2026-09-13T06:00:00+00:00",
        last_change=last_change,
    )


class ReportTests(unittest.TestCase):
    def test_tabs_and_new_window_links(self) -> None:
        html = render_report([sample("new"), replace(sample(""), listing_id="2")])
        self.assertIn('data-tab="new"', html)
        self.assertIn('data-tab="all"', html)
        self.assertIn('target="_blank"', html)
        self.assertIn('thumbs/bikemaster-65159.jpg', html)
        self.assertIn("New (1)", html)
        self.assertIn("All (2)", html)
        self.assertIn('data-tab="favorites"', html)
        self.assertIn('data-listing-key="bikemaster:65159"', html)
        self.assertIn('id="new" class="panel active"', html)
        self.assertIn("Favorite", html)
        self.assertIn("localStorage", html)
        self.assertNotIn("Scrape", html)
        self.assertNotIn("Reset database", html)

    def test_empty_new_tab_is_still_default(self) -> None:
        html = render_report([sample("")])
        self.assertIn('id="new" class="panel active"', html)
        self.assertIn("New (0)", html)
        self.assertIn("No new listings.", html)
        self.assertNotIn('id="all" class="panel active"', html)

    def test_missing_db_is_recreated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing" / "seen.db"
            self.assertFalse(path.exists())
            store = Store(path)
            self.assertTrue(path.exists())
            self.assertTrue(store.is_empty())
            store.close()
