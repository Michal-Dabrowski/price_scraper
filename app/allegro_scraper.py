# -*- coding: utf-8 -*-

import json
import random
import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from app import db
from app.models import SuggestedPrices

class Product:
    def __init__(self):
        self.dealer_name = ''
        self.full_name = ''
        self.url = ''
        self.price = 0
        self.dealer_id = ''
        self.free_shipping = False
        self.new = False
        self.product_name = ''
        self.suggested_price = 0
        self.price_too_low = False
        self.percentage_decrease = 0

    def create_product_dict(self):
        return self.__dict__

class AllegroScraper:

    def __init__(self, brand_name):
        self.brand_name = brand_name
        headers = requests.utils.default_headers()
        headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:52.0) Gecko/20100101 Firefox/52.0'})
        self.headers = headers
        self.last_page = 1
        self.current_page = 1
        self.products_list = []
        self.current_page_soup = None
        self.current_progress_bar_percent_value = 0

    def search_soup_for_json_object(self, soup):
        """
        Allegro keeps products in a json object in
        "window.__listing_ItemsStoreRawData" variable in <script> in their HTML code

        :param soup
        :return json object containing products data
        """
        raw_data = soup.find_all('script')
        p = re.compile('window.__listing_ItemsStoreRawData = (.*);')
        for element in raw_data:
            try:
                if "window.__listing_ItemsStoreRawData =" in element.string:
                    m = p.search(element.string)
                    data = m.group(1)
                    data = data.replace('(', '[')
                    data = data.replace(')', ']')
                    data = data.replace('new Date', '')
                    json_object = json.loads(data)
                    json_object = json_object['items']['items']
                    return json_object
            except TypeError:  # some elements are NoneType
                pass

    def get_products_from_json_object(self, json_object):
        """
        :param json_object:
        :return: returns a list of dictionaries containing products data
        """
        products_list = list()
        for item in json_object:
            if 'buyNow' in item['sellingMode']:  #filters out 'auctions'
                try:
                    product = Product()
                    name_and_suggested_price = self.detect_name_and_suggested_price(
                        item['name'])  # generates None for discontinued products
                    price = float(item['sellingMode']['buyNow']['price']['amount'])
                    suggested_price = float(name_and_suggested_price['suggested_price'].replace(',', '.'))

                    product.full_name = item['name']
                    product.source = 'allegro'
                    product.url = item['url']
                    product.price = price
                    product.dealer_id = item['seller']['id']
                    product.dealer_name = ''
                    product.free_shipping = item['shipping']['freeDelivery']
                    product.new = item['parameters'][0]['values'][0] == 'Nowy'
                    product.product_name = name_and_suggested_price['name']
                    product.suggested_price = suggested_price
                    product.price_too_low = price < suggested_price
                    product.percentage_decrease = self.count_percentage_decrease(suggested_price, price)

                    product_dict = product.create_product_dict()
                    products_list.append(product_dict)
                except (TypeError,
                        IndexError):  # 'NoneType' for None objects, IndexError for item['attributes'][0]['values'][0] == 'Nowy'
                    pass
        return products_list

    def detect_last_page(self, soup):
        try:
            last_page = soup.find('li', class_="quantity")
            last_page = last_page.text
            last_page = int(re.search(r'\d+', last_page).group())
        except:
            print("Couldn't find the last page! Setting the last page to '20'.")
            last_page = 20
        return last_page

    def print_feedback(self):
        percent = round(self.current_page / self.last_page * 100, 1)
        self.current_progress_bar_percent_value = percent
        print("Scraping page {} from {}. Progress: {}%".format(self.current_page, self.last_page, percent))

    @staticmethod
    def count_percentage_decrease(regular_price, dealer_price):
        percent = dealer_price / regular_price
        percent = percent * 100
        percent = percent - 100
        return round(percent, 2)

    def generator(self):
        with requests.Session() as s:
            while self.current_page <= self.last_page:
                s.headers = self.headers
                response = s.get(
                    url="https://allegro.pl/listing?string=" + self.brand_name +
                        "&order=m&bmatch=base-relevance-floki-5-nga-hc-ele-1-2-0901&p=" +
                        str(self.current_page))
                self.current_page_soup = BeautifulSoup(response.content, "html.parser")
                self.last_page = self.detect_last_page(self.current_page_soup)
                json_object = self.search_soup_for_json_object(self.current_page_soup)
                self.products_list += self.get_products_from_json_object(json_object['regular'])
                self.products_list += self.get_products_from_json_object(json_object['promoted'])
                self.print_feedback()
                self.current_page += 1
                yield str(self.current_progress_bar_percent_value)
                time.sleep(random.uniform(15, 30))

if __name__ == '__main__':
    scraper = AllegroScraper()