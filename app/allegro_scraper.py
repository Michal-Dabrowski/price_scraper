# -*- coding: utf-8 -*-

import json
import random
import re
import time
import requests
from bs4 import BeautifulSoup
from .models import detect_name_and_suggested_price, count_percentage_decrease

class Product:
    def __init__(self):
        self.type = None #buynow or auction
        self.dealer_name = None
        self.full_name = None
        self.url = None
        self.price = None
        self.dealer_id = None
        self.free_shipping = None
        self.shipping_costs = None
        self.new = None
        self.product_name = None
        self.archive = None
        self.suggested_price = None
        self.price_too_low = None
        self.percentage_decrease = None

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
        "window.__listing_ItemsStoreState" variable in <script> in their HTML code

        :param soup
        :return json object containing products data
        """
        raw_data = soup.find_all('script')
        p = re.compile('window.__listing_ItemsStoreState = (.*);')
        for element in raw_data:
            try:
                if "window.__listing_ItemsStoreState =" in element.string:
                    m = p.search(element.string)
                    data = m.group(1)
                    json_object = json.loads(data)
                    return json_object
            except TypeError:  # some elements are NoneType
                pass

    def get_products_from_json_object(self, json_object):
        """
        :param json_object:
        :return: returns a list of dictionaries containing products data
        """
        products_list = list()
        for item in json_object['items']:
            try:
                product = Product()
                product.type = self.get_type(item)
                product.full_name = self.get_name(item)
                product.source = 'allegro'
                product.url = self.get_url(item)
                product.price = self.get_price(item)
                product.dealer_id = self.get_dealer_id(item)
                product.free_shipping = self.free_shipping(item)
                product.shipping_costs = self.get_shipping_costs(item)
                product.new = self.is_product_new(item)
                product.archive = self.is_archived(item)
                product_dict = product.create_product_dict()
                products_list.append(product_dict)
            except (TypeError, IndexError):
                pass
        return products_list

    def get_type(self, product):
        return product['type']

    def is_product_new(self, product):
        return product['attributes'][0]['value'] == 'Nowy'

    def free_shipping(self, product):
        try:
            return product['deliveryInfo'][0]['name'] == 'freeDelivery'
        except KeyError:
            return False

    def get_shipping_costs(self, product):
        try:
            return product['deliveryInfo'][0]['price']['amount']
        except KeyError:
            return None

    def get_dealer_id(self, product):
        return product['userInfo']['sellerId']

    def get_url(self, product):
        return product['url']

    def is_archived(self, product):
        return product['isEnded']

    def get_name(self, product):
        return str(product['title']['text'])

    def get_price(self, product):
        return float(product['price']['normal']['amount'])

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

    def update_names_and_suggested_prices(self):
        for product in self.products_list:
            try:
                name_and_price = detect_name_and_suggested_price(product['full_name'])
                product['product_name'] = name_and_price['name']
                product['suggested_price'] = name_and_price['suggested_price']
                product['percentage_decrease'] = count_percentage_decrease(product['suggested_price'], product['price'])
                product['price_too_low'] = product['price'] < product['suggested_price']
            except TypeError:
                pass

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
                for group in json_object['itemsGroups']:
                    self.products_list += self.get_products_from_json_object(group)
                self.print_feedback()
                self.current_page += 1
                yield str(self.current_progress_bar_percent_value)
                time.sleep(random.uniform(2, 5))
        self.update_names_and_suggested_prices()

if __name__ == '__main__':
    scraper = AllegroScraper('playstation 4')
    generator = scraper.generator()
    for step in generator:
        print(step)