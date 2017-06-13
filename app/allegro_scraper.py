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
    """
    item_type is only for allegro
    """
    def __init__(self):
        self.dealer_name = ''
        self.full_name = ''
        self.url = ''
        self.price = 0
        self.dealer_id = ''
        self.free_shipping = False
        self.item_type = ''
        self.new = False
        self.product_name = ''
        self.suggested_price = 0
        self.price_too_low = False
        self.percentage_decrease = 0

    def create_product_dict(self):
        return self.__dict__

def scrap_allegro(brand_name):
    """
    :param brand_name: brand name we want to scrap
    :return: returns a list containing products dictionaries for every page:
    """
    analysis_list = []
    page_number = 1
    last_page = 1
    headers = requests.utils.default_headers()
    headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:52.0) Gecko/20100101 Firefox/52.0'})
    with requests.Session() as s:
        while page_number <= last_page:
            s.headers = headers
            response = s.get(
                url="https://allegro.pl/listing?string=" + brand_name +
                "&order=m&bmatch=base-relevance-floki-5-nga-ele-1-2-0403&p=" +
                str(page_number))
            soup = BeautifulSoup(response.content, "html.parser")
            last_page = detect_last_page(soup)
            json_object = search_soup_for_json_object(soup)
            analysis_list += analyze_products_from_json_object(json_object)
            print("Scraping page {} from {}".format(page_number, last_page))
            page_number += 1
            time.sleep(random.uniform(15, 30))
    return analysis_list

def detect_last_page(soup):
    try:
        last_page = soup.find('li', class_="quantity")
        last_page = last_page.text
        last_page = int(re.search(r'\d+', last_page).group())
    except:
        print("Couldn't find the last page! Setting the last page to '20'.")
        last_page = 20
    return last_page

def search_soup_for_json_object(soup):
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
                json_object = json.loads(m.group(1))
                json_object = json_object['items']['items']
                return json_object
        except TypeError:  # some elements are NoneType
            pass

def analyze_products_from_json_object(json_object):
    """
    :param json_object:
    :return: returns a list of dictionaries containing products data
    """
    products_list = list()
    for item in json_object:
        try:
            product = Product()
            name_and_suggested_price = detect_name_and_suggested_price(item['name'])  # generates None for discontinued products
            price = int(item['buyNowPrice'])
            suggested_price = float(name_and_suggested_price['suggested_price'].replace(',', '.'))

            product.full_name = item['name']
            product.source = 'allegro'
            product.url = item['url']
            product.price = price
            product.dealer_id = item['sellerId']
            product.dealer_name = ''
            product.free_shipping = item['freeShipping']
            product.item_type = item['itemType']
            product.new = item['attributes'][0]['values'][0] == 'Nowy'
            product.product_name = name_and_suggested_price['name']
            product.suggested_price = suggested_price
            product.price_too_low = price < suggested_price
            product.percentage_decrease = count_percentage_decrease(suggested_price, price)

            product_dict = product.create_product_dict()
            products_list.append(product_dict)
        except (TypeError, IndexError):  # 'NoneType' for None objects, IndexError for item['attributes'][0]['values'][0] == 'Nowy'
            pass
    return products_list

def detect_name_and_suggested_price(name):
    name = name.lower()

    for element in ['pokrywa', 'kufer', 'case', 'igła', 'headshell', 'decksaver',
                    'cable', 'kabel', 'statyw', 'laptop', 'stand', 'puck', 'adapter',
                    'szczoteczka', 'ear pack', 'fader cap', 'knob cap', 'pasek', 'adaptor', 'gooseneck', 'stylus']:
        if element in name:
            return None

    suggested_prices_sql_table = SuggestedPrices.query.all()
    for row in suggested_prices_sql_table:
        match = re.search(row.product_name_regex_pattern, name)
        if match:
            return {'name': row.product_name, 'suggested_price' : row.suggested_price}

def count_percentage_decrease(regular_price, dealer_price):
    percent = dealer_price / regular_price
    percent = percent * 100
    percent = percent - 100
    return round(percent, 2)