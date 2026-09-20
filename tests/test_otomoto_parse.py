from __future__ import annotations

import json
import unittest

from bike_scraper.sites.otomoto import parse_listings, with_page


def _html(search: dict) -> str:
    payload = {
        "props": {
            "pageProps": {
                "urqlState": {
                    "1": {"data": json.dumps({"advertSearch": search})}
                }
            }
        }
    }
    return f'<html><script id="__NEXT_DATA__">{json.dumps(payload)}</script></html>'


class OtomotoParseTests(unittest.TestCase):
    def test_with_page(self) -> None:
        url = "https://www.otomoto.pl/motocykle-i-quady/mv-agusta/od-2013?search%5Bfilter_float_price%3Ato%5D=25000"
        self.assertEqual(with_page(url, 1), url)
        self.assertIn("page=2", with_page(url, 2))

    def test_parse_listing(self) -> None:
        html = _html(
            {
                "totalCount": 1,
                "pageInfo": {"pageSize": 32, "currentOffset": 0},
                "edges": [
                    {
                        "node": {
                            "id": "6147996245",
                            "title": "MV AGUSTA Brutale",
                            "shortDescription": "800rr. Ideał.",
                            "url": "https://www.otomoto.pl/motocykle-i-quady/oferta/mv-agusta-brutale-ID6I4mFL.html",
                            "price": {"amount": {"units": 24000, "value": "24000"}},
                            "location": {
                                "city": {"name": "Tychy"},
                                "region": {"name": "Śląskie"},
                            },
                            "parameters": [
                                {"key": "year", "displayValue": "2016", "value": "2016"},
                                {"key": "mileage", "displayValue": "51259 km", "value": "51259"},
                                {"key": "engine_capacity", "displayValue": "800 cm3", "value": "800"},
                            ],
                            "thumbnail": {
                                "x1": "https://example.com/thumb.jpg",
                            },
                        }
                    }
                ],
            }
        )
        listings, total, page_size, offset = parse_listings(html)
        self.assertEqual((total, page_size, offset), (1, 32, 0))
        self.assertEqual(len(listings), 1)
        listing = listings[0]
        self.assertEqual(listing.site, "otomoto")
        self.assertEqual(listing.listing_id, "6147996245")
        self.assertEqual(listing.price_pln, 24000)
        self.assertEqual(listing.image_url, "https://example.com/thumb.jpg")
        self.assertIn("2016", listing.snippet)
        self.assertIn("Tychy", listing.snippet)
        self.assertIn("800rr", listing.snippet)

    def test_missing_data_raises(self) -> None:
        with self.assertRaises(RuntimeError):
            parse_listings("<html><title>blocked</title></html>")
