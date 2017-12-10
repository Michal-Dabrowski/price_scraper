# -*- coding: utf-8 -*-

import unittest
from app.allegro_scraper import AllegroScraper, Product
from bs4 import BeautifulSoup

url = "https://allegro.pl/listing?string=reloop&order=m&bmatch=base-relevance-floki-5-nga-hc-ele-1-2-0901&p=1"
with open('allegro.txt', 'rb') as file:
    content = file.read()
test_soup = BeautifulSoup(content, 'html.parser')
scraper = AllegroScraper('')
test_product = scraper.search_soup_for_json_object(test_soup)['itemsGroups'][0]['items'][0]

class SearchSoupForJsonObjectTestCase(unittest.TestCase):

    def test_if_soup_has_json_(self):
        scraper = AllegroScraper('')
        with self.assertRaises(AttributeError):
            scraper.search_soup_for_json_object('trdxcgg')

    def test_if_soup_has_json(self):
        """Is the JSON object returned by the search_soup_for_json_object method?"""
        scraper = AllegroScraper('')
        self.assertIsNotNone(scraper.search_soup_for_json_object(test_soup))

class ProductIsBuynowOptionTestCase(unittest.TestCase):

    def test_buynow(self):
        test_product_buynow = {'label': {'className': 'buy-now'}}
        self.assertEqual(scraper.get_type(test_product_buynow), 'buynow')

    def test_auction(self):
        test_product_auction = {'label': {'className': 'auction'}}
        self.assertEqual(scraper.get_type(test_product_auction), 'auction')

class IsProductNewTestCase(unittest.TestCase):

    def test_new(self):
        product = {'parameters': [{'values': ['Nowy']}]}

