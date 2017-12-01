# -*- coding: utf-8 -*-

import unittest
from app.allegro_scraper import AllegroScraper, Product
from bs4 import BeautifulSoup

url = "https://allegro.pl/listing?string=reloop&order=m&bmatch=base-relevance-floki-5-nga-hc-ele-1-2-0901&p=1"
with open('allegro.txt', 'rb') as file:
    content = file.read()
test_soup = BeautifulSoup(content, 'html.parser')
scraper = AllegroScraper('')
test_product = scraper.search_soup_for_json_object(test_soup)['regular'][0]

class SearchSoupForJsonObjectTestCase(unittest.TestCase):

    def test_if_soup_has_json_(self):
        scraper = AllegroScraper('')
        with self.assertRaises(AttributeError):
            scraper.search_soup_for_json_object('trdxcgg')

    def test_if_soup_has_json(self):
        """Is the JSON object returned by the search_soup_for_json_object method?"""
        scraper = AllegroScraper('')
        self.assertIsNotNone(scraper.search_soup_for_json_object(test_soup))

    def test_if_json_has_promoted_items(self):
        scraper = AllegroScraper('')
        assert 'promoted' in scraper.search_soup_for_json_object(test_soup)

    def test_if_json_has_regular_items(self):
        scraper = AllegroScraper('')
        assert 'regular' in scraper.search_soup_for_json_object(test_soup)

    def test_if_json_has_sponsored_items(self):
        scraper = AllegroScraper('')
        assert 'sponsored' in scraper.search_soup_for_json_object(test_soup)

class ProductIsBuynowOptionTestCase(unittest.TestCase):

    def test_buynow(self):
        scraper = AllegroScraper('')
        assert  scraper.product_is_buynow_option(test_product)