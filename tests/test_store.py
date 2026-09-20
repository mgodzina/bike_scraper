from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bike_scraper.models import Listing
from bike_scraper.runner import collect_findings
from bike_scraper.store import Store


def listing(listing_id: str = "1", price: int | None = 16900) -> Listing:
    return Listing(
        site="bikemaster",
        listing_id=listing_id,
        url=f"https://bikemaster.pl/motocykle/bike-{listing_id}/",
        title=f"Bike {listing_id}",
        category="available",
        price_pln=price,
        old_price_pln=None,
        snippet="",
    )


class StoreTests(unittest.TestCase):
    def test_first_run_then_new_and_price_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "seen.db")
            first = collect_findings(store, [listing("1", 16900)])
            self.assertEqual([item.kind for item in first], ["new"])

            same = collect_findings(store, [listing("1", 16900)])
            self.assertEqual([item.kind for item in same], ["seen"])

            cheaper = collect_findings(store, [listing("1", 15000)])
            self.assertEqual(cheaper[0].kind, "price_change")
            self.assertEqual(cheaper[0].previous_price, 16900)

            fresh = collect_findings(store, [listing("2", 20000)])
            self.assertEqual(fresh[0].kind, "new")
            store.close()
