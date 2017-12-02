# -*- coding: utf-8 -*-

import unittest
from app.allegro_scraper import AllegroScraper, Product
from bs4 import BeautifulSoup

url = "https://allegro.pl/listing?string=reloop&order=m&bmatch=base-relevance-floki-5-nga-hc-ele-1-2-0901&p=1"
with open('allegro.txt', 'rb') as file:
    content = file.read()
test_soup = BeautifulSoup(content, 'html.parser')
scraper = AllegroScraper('')


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
        self.assertTrue('promoted' in scraper.search_soup_for_json_object(test_soup))

    def test_if_json_has_regular_items(self):
        scraper = AllegroScraper('')
        self.assertTrue('regular' in scraper.search_soup_for_json_object(test_soup))

    def test_if_json_has_sponsored_items(self):
        scraper = AllegroScraper('')
        self.assertTrue('sponsored' in scraper.search_soup_for_json_object(test_soup))

class ProductIsBuynowOptionTestCase(unittest.TestCase):

    def test_buynow(self):
        test_product_buynow = {'sellingMode': {'sellingMode': 'buyNow'}}
        self.assertTrue(scraper.product_is_buynow_option(test_product_buynow))

    def test_auction(self):
        test_product_auction = {'sellingMode': {'sellingMode': 'auction'}}
        self.assertFalse(scraper.product_is_buynow_option(test_product_auction))

class IsProductNewTestCase(unittest.TestCase):

    def test_new(self):
        product = {'parameters': [{'values': ['Nowy']}]}





json = {'vendor': 'allegro',
        'location': {'city': 'Kraków',
                     'country': 'PL'
                     },
        'name': 'Reloop Beatmix 2 Mk2 kontroler DJ+słuchawki GRATIS',
        'parameters': [{'highlight': False,
                        'values': ['Nowy'],
                        'name': 'Stan'
                        }
                       ],
        'id': '7056549951',
        'seller': {'superSeller': True,
                   'id': '7292182'},
        'url': 'http://allegro.pl/reloop-beatmix-2-mk2-kontroler-dj-sluchawki-gratis-i7056549951.html',
        'coins': {'total': {'quantity': 0}
                  },
        'images': [{'url': 'https://7.allegroimg.com/original/019d2c/0eb579e14af6a0822f846631a2d7'}],
        'categoryPath': [{'id': '122332'},
                         {'id': '122370'},
                         {'id': '122371'}
                         ],
        'quantity': {'value': 9, 'unitType': 'UNIT'},
        'sellingMode': {'sellingMode': 'auction',
                        'buyNow': {'cartAvailable': True,
                                   'popularity': 1,
                                   'price': {'currency': 'PLN',
                                             'amount': '765.00'}
                                   }
                        },
        'shipping': {'lowest': {'currency': 'PLN',
                                'amount': '0.00'
                                },
                     'itemWithDelivery': {'currency': 'PLN',
                                          'amount': '765.00'
                                          },
                     'freeDeliveryWeek': False,
                     'freeDelivery': True,
                     'freeReturn': True},
        'promotion': {'bold': False,
                      'highlight': False,
                      'emphasized': False}
        }
