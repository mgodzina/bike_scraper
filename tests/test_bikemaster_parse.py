from __future__ import annotations

import unittest

from bike_scraper.sites.bikemaster import next_page_url, parse_listings, parse_pln, search_url

SALE_HTML = """
<ul id="archive-container">
  <div class="custom-archive-loop-item entry post-65159 motocykle dostepny-dostepny-teraz">
    <figure><img src="https://bikemaster.pl/big.jpg" srcset="https://bikemaster.pl/small.jpg 300w, https://bikemaster.pl/big.jpg 1920w"></figure>
    <a href="https://bikemaster.pl/motocykle/mv-agusta-brutale-910-zarejestrowany-w-polsce/" class="kb-advanced-heading-link">
      <h2>MV AGUSTA BRUTALE 910 Zarejestrowany w Polsce !</h2>
    </a>
    <h3 class="przecena">19 900 zł</h3>
    <h3>16 900 zł</h3>
    <p>MV Agusta Brutale 910, przebieg to 30788 km.</p>
  </div>
</ul>
<nav class="pagination">
  <a class="next page-numbers" href="https://bikemaster.pl/dostepny/dostepny-teraz/page/2/?s=suzuki">2</a>
</nav>
"""

EMPTY_HTML = """
<section class="error">
  <p>Przepraszamy, ale nie znaleziono wyników zgodnych z parametrami wyszukiwania.</p>
</section>
"""


class BikemasterParseTests(unittest.TestCase):
    def test_search_urls(self) -> None:
        self.assertEqual(
            search_url("available", "agusta"),
            "https://bikemaster.pl/dostepny/dostepny-teraz/?s=agusta",
        )
        self.assertEqual(
            search_url("upcoming", "agusta", page=1),
            "https://bikemaster.pl/dostepny/dostepny-wkrotce/?s=agusta",
        )
        self.assertEqual(
            search_url("available", "suzuki", page=2),
            "https://bikemaster.pl/dostepny/dostepny-teraz/page/2/?s=suzuki",
        )

    def test_parse_sale_card(self) -> None:
        listings = parse_listings(SALE_HTML, "available")
        self.assertEqual(len(listings), 1)
        listing = listings[0]
        self.assertEqual(listing.listing_id, "65159")
        self.assertEqual(listing.title, "MV AGUSTA BRUTALE 910 Zarejestrowany w Polsce !")
        self.assertEqual(listing.price_pln, 16900)
        self.assertEqual(listing.old_price_pln, 19900)
        self.assertTrue(listing.url.endswith("mv-agusta-brutale-910-zarejestrowany-w-polsce/"))
        self.assertIn("30788", listing.snippet)
        self.assertEqual(listing.image_url, "https://bikemaster.pl/small.jpg")

    def test_empty_results(self) -> None:
        self.assertEqual(parse_listings(EMPTY_HTML, "upcoming"), [])
        self.assertIsNone(next_page_url(EMPTY_HTML))

    def test_next_page(self) -> None:
        self.assertEqual(
            next_page_url(SALE_HTML),
            "https://bikemaster.pl/dostepny/dostepny-teraz/page/2/?s=suzuki",
        )

    def test_parse_pln(self) -> None:
        self.assertEqual(parse_pln("16 900 zł"), 16900)
        self.assertEqual(parse_pln("32\u00a0900 zł"), 32900)
        self.assertIsNone(parse_pln("no price here"))


if __name__ == "__main__":
    unittest.main()
