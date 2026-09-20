from __future__ import annotations

import json
import unittest

from bike_scraper.sites.autoplac import parse_listings


def _html(body: dict) -> str:
    payload = {
        "https://api.autoplac.pl/offers/search?yearFrom=2013&seoCategories=motocykle,mv-agusta,cena-do-25-tysiecy": {
            "status": 200,
            "body": body,
        }
    }
    return f'<html><script id="ng-state" type="application/json">{json.dumps(payload)}</script></html>'


class AutoplacParseTests(unittest.TestCase):
    def test_parse_listing(self) -> None:
        html = _html(
            {
                "offerCount": 1,
                "offerList": [
                    {
                        "photoList": [
                            {
                                "miniatureUrl": "https://example.com/thumb.webp",
                            }
                        ],
                        "offer": {
                            "id": 4501358,
                            "title": "MV Agusta Brutale 800 RR 800rr.",
                            "webUrl": "/oferta/mv-agusta/brutale-800-rr/2016r-800rr-4465-8998-TJ",
                            "productionYear": 2016,
                            "mileage": 51000,
                            "engineCapacity": 800,
                            "city": "Tychy",
                            "voivodeshipDisplay": "Śląskie",
                            "priceInfo": {"primary": {"price": 24000}},
                        },
                    }
                ],
            }
        )
        listings = parse_listings(html)
        self.assertEqual(len(listings), 1)
        listing = listings[0]
        self.assertEqual(listing.site, "autoplac")
        self.assertEqual(listing.listing_id, "4501358")
        self.assertEqual(listing.price_pln, 24000)
        self.assertEqual(
            listing.url,
            "https://autoplac.pl/oferta/mv-agusta/brutale-800-rr/2016r-800rr-4465-8998-TJ",
        )
        self.assertEqual(listing.image_url, "https://example.com/thumb.webp")
        self.assertIn("2016", listing.snippet)
        self.assertIn("Tychy", listing.snippet)
        self.assertIn("51 000 km", listing.snippet)

    def test_missing_data_raises(self) -> None:
        with self.assertRaises(RuntimeError):
            parse_listings("<html><title>blocked</title></html>")
