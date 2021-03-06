# -*- coding: utf-8 -*-

import unittest
from unittest.mock import patch, Mock, MagicMock
import json
from app.allegro_scraper import AllegroScraper, Product
from bs4 import BeautifulSoup

class SearchSoupForJsonObjectTestCase(unittest.TestCase):

    def setUp(self):
        self.scraper = AllegroScraper('')
        with open('allegro.txt', 'rb') as file:
            content = file.read()
        self.test_soup = BeautifulSoup(content, 'html.parser')

    def test_if_soup_has_json_(self):
        with self.assertRaises(AttributeError):
            self.scraper.search_soup_for_json_object('trdxcgg')

    def test_if_soup_has_json(self):
        """Is the JSON object returned by the search_soup_for_json_object method?"""
        self.assertIsNotNone(self.scraper.search_soup_for_json_object(self.test_soup))

class ProductIsBuynowOptionTestCase(unittest.TestCase):

    def setUp(self):
        self.scraper = AllegroScraper('')

    def test_buynow(self):
        test_product_buynow = {'type': 'buyNow'}
        self.assertEqual(self.scraper.get_type(test_product_buynow), 'buyNow')

    def test_auction(self):
        test_product_auction = {'type': 'auction'}
        self.assertEqual(self.scraper.get_type(test_product_auction), 'auction')

class IsProductNewTestCase(unittest.TestCase):

    def setUp(self):
        self.scraper = AllegroScraper('')

    def test_new(self):
        product = {'attributes': [{'value': 'Nowy'}]}
        self.assertTrue(self.scraper.is_product_new(product))

    def test_used(self):
        product = {'attributes': [{'value': 'Używany'}]}
        self.assertFalse(self.scraper.is_product_new(product))

class FreeShippingTestCase(unittest.TestCase):

    def setUp(self):
        self.scraper = AllegroScraper('')

    def test_free_shipping(self):
        product = {'deliveryInfo': [{'name': 'freeDelivery'}]}
        self.assertTrue(self.scraper.free_shipping(product))

    def test_not_free_shipping(self):
        product = {'deliveryInfo': [{'name': 'noFreeShipping'}]}
        self.assertFalse(self.scraper.free_shipping(product))

    def test_missing_free_shipping(self):
        product = {}
        self.assertFalse(self.scraper.free_shipping(product))

class GetShippingCostsTestCase(unittest.TestCase):

    def setUp(self):
        self.scraper = AllegroScraper('')

    def test_shipping_costs(self):
        product = {'deliveryInfo': [{'price': {'amount': 10.5}}]}
        self.assertEqual(self.scraper.get_shipping_costs(product), 10.5)

    def test_no_shipping_costs(self):
        product = {}
        self.assertIsNone(self.scraper.get_shipping_costs(product))

class GetDealerIdTestCase(unittest.TestCase):

    def setUp(self):
        self.scraper = AllegroScraper('')

    def test_dealer_id(self):
        product = {'userInfo': {'sellerId': 456853}}
        self.assertEqual(self.scraper.get_dealer_id(product), 456853)

class GetUrlTestCase(unittest.TestCase):

    def setUp(self):
        self.scraper = AllegroScraper('')

    def test_url(self):
        product = {'url': 'www.example.com/product'}
        self.assertEqual(self.scraper.get_url(product), 'www.example.com/product')

class IsArchivedTestCase(unittest.TestCase):

    def setUp(self):
        self.scraper = AllegroScraper('')

    def test_is_archived_false(self):
        product = {'isEnded': False}
        self.assertFalse(self.scraper.is_archived(product))

    def test_is_archived_true(self):
        product = {'isEnded': True}
        self.assertTrue(self.scraper.is_archived(product))

class GetNameTestCase(unittest.TestCase):

    def setUp(self):
        self.scraper = AllegroScraper('')

    def test_string_name(self):
        product = {'title': {'text': 'Product Name'}}
        self.assertEqual(self.scraper.get_name(product), 'Product Name')

    def test_int_name(self):
        product = {'title': {'text': 3648}}
        self.assertEqual(self.scraper.get_name(product), '3648')

    def test_no_name(self):
        product = {'title': {}}
        with self.assertRaises(KeyError):
            self.scraper.get_name(product)

class DetectLastPageTestCase(unittest.TestCase):

    def setUp(self):
        self.scraper = AllegroScraper('')

    @patch('app.allegro_scraper.BeautifulSoup')
    def test_detect_last_page(self, mock_soup):
        mock_tag = MagicMock()
        mock_tag.text = '<li class="quantity"><a href="#" rel="last">487</a></li>'
        mock_soup.find.return_value = mock_tag
        self.assertEqual(self.scraper.detect_last_page(mock_soup), 487)

    @patch('app.allegro_scraper.BeautifulSoup')
    def test_no_last_page(self, mock_soup):
        mock_tag = MagicMock()
        mock_tag.text = '<li class="quantity"><a href="#" rel="last"></a></li>'
        mock_soup.find.return_value = mock_tag
        self.assertEqual(self.scraper.detect_last_page(mock_soup), 20)

class PrintFeedbackTestCase(unittest.TestCase):

    def setUp(self):
        self.scraper = AllegroScraper('')

    def test_print_feedback_50_percent(self):
        self.scraper.last_page = 20
        self.scraper.current_page = 10
        self.scraper.print_feedback()
        self.assertEqual(self.scraper.current_progress_bar_percent_value, 50)