# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import requests
import re
import time
import random
from app.allegro_scraper import Product, AllegroScraper

class CeneoUrlScraper:

    def __init__(self):
        self.url_list = []
        self.current_progress_bar_percent_value = 0
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:54.0) Gecko/20100101 Firefox/54.0'})

    def detect_last_page(self, soup):
        try:
            last_page = soup.find('div', class_="pagination-top")
            last_page = last_page.text
            last_page = int(re.search(r'\d+', last_page).group())
        except:
            print("Couldn't find the last page! Setting the last page to '20'.")
            last_page = 20  # we probably don't need more... probably
        return last_page - 1

    def get_urls_with_names_from_ceneo_page(self, soup):
        urls = dict()

        products = soup.find_all('div', class_='cat-prod-row-desc')
        for product in products:
            product = product.find_all('a', class_=" js_conv")
            for element in product:
                product = element.text
                url = element.get('href')
                urls[str(product)] = str(url)
        return urls

    def print_feedback(self, page_number, last_page):
        percent = round(page_number / last_page * 100, 1)
        self.current_progress_bar_percent_value = percent
        print("Scraping page {} from {}. Progress: {}%".format(page_number, last_page, percent))

    def main(self, brand_name):
        current_page_number = 0
        last_page_number = 0
        while current_page_number <= last_page_number:
            if current_page_number == 0:
                response = self.session.get('http://www.ceneo.pl/;szukaj-' + str(brand_name))
            else:
                response = self.session.get('http://www.ceneo.pl/;szukaj-' + str(brand_name) + ';0020-30-0-0-' + str(current_page_number) + '.htm')
            current_page_soup = BeautifulSoup(response.content)
            current_page_number += 1
            last_page_number = self.detect_last_page(current_page_soup)
            self.url_list.append(self.get_urls_with_names_from_ceneo_page(current_page_soup))
            self.print_feedback(current_page_number, last_page_number + 1)
            yield self.current_progress_bar_percent_value
            time.sleep(random.uniform(15, 35))
        random.shuffle(self.url_list)
        print('{} urls collected'.format(len(self.url_list)))

class CeneoScraper:

    def __init__(self, url_list):
        self.products_list = []
        self.current_progress_bar_percent_value = 0
        self.url_list = url_list

        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:54.0) Gecko/20100101 Firefox/54.0'})

    def set_current_progress(self, percent):
        self.current_progress_bar_percent_value = percent

    def get_percent(self, page_number, last_page):
        percent = round(page_number / last_page * 100, 1)
        return percent

    def filter_out_unwanted_products(self, list):
        """
        Takes a list of names or list of dictionaries containing product names (the name should be under 'name' key),
        and checks if a name is in the database. Creates a new list or dict with only the names that are in the database.

        :param list: a list of names or dictionaries containing names
        :return: a new list containing only products that are in the database
        """
        new_dict = dict()
        for element in list:
            if isinstance(element, dict):
                for key, value in element.items():
                    if self.filter_name(key):
                        new_dict[key] = value
        return new_dict

    def filter_name(self, name):
        name = AllegroScraper.detect_name_and_suggested_price(name)
        if name is not None:
            return True
        return False

    def detect_last_page(self, soup):
        try:
            last_page = soup.find('div', class_="pagination-top")
            last_page = last_page.text
            last_page = int(re.search(r'\d+', last_page).group())
        except:
            print("Couldn't find the last page! Setting the last page to '20'.")
            last_page = 20  # we probably don't need more... probably
        return last_page - 1

    def get_products_from_ceneo_page(self, url):
        response = self.session.get('http://www.ceneo.pl/' + url)
        soup = BeautifulSoup(response.content)

        promoted_products = soup.find_all('table', class_="product-offers js_product-offers")
        regular_products = soup.find_all('table', class_="product-offers js_product-offers js_normal-offers ")
        promoted_products_list = self.get_products_from_result_set(promoted_products, url)
        regular_products_list = self.get_products_from_result_set(regular_products, url)
        return promoted_products_list + regular_products_list

    def get_products_from_result_set(self, result_set, url):
        """
        Creates a Product class instance

        :param result_set: result set from bs4.find_all()
        :param url: source url
        :return: list of all products found in the result set
        """
        products_list = []
        for soup in result_set:
            products = self.get_products(soup)
            for item in products:
                offer_id = self.get_offer_id(item)
                shop_id = self.get_shop_id(item)
                price = self.get_correct_price(result_set, offer_id, shop_id)
                try:
                    product = Product()
                    product.source = 'ceneo'
                    product.dealer_name = self.get_dealer_name(item)
                    product.price = float(price)
                    product.dealer_id = shop_id
                    product.full_name = self.get_product_full_name(item)
                    product.url = 'http://www.ceneo.pl' + url
                    product.new = True
                    name_and_suggested_price = AllegroScraper.detect_name_and_suggested_price(product.full_name)  # generates None for discontinued products
                    product.suggested_price = float(name_and_suggested_price['suggested_price'].replace(',', '.'))
                    product.product_name = name_and_suggested_price['name']
                    product.price_too_low = product.price < product.suggested_price
                    product.percentage_decrease = AllegroScraper.count_percentage_decrease(product.suggested_price,
                                                                                               product.price)
                    products_list.append(product.__dict__)
                except TypeError:  # 'NoneType' object is not subscriptable
                    pass
        return products_list

    def get_products(self, soup):
        return soup.find_all('tr', class_="product-offer js_product-offer")

    def get_offer_id(self, item):
        return item.get('data-offer')

    def get_shop_id(self, item):
        return item.get('data-shop')

    def get_dealer_name(self, item):
        return item.get('data-shopurl')

    def get_product_full_name(self, item):
        return item.find('span', class_="short-name__txt").text

    def get_correct_price(self, result_set, offer_id, shop_id):
        for element in result_set:
            validators = element.find_all('tr', class_="details-row js_product-offer")
            for element in validators:
                if element.get('data-offer') == offer_id and element.get('data-shop') == shop_id:
                    price = element.get('data-offer-price')
                    return price

    def main(self):
        for index, url in enumerate(self.url_list):
            self.products_list += self.get_products_from_ceneo_page(url)
            percent = self.get_percent(index + 1, len(self.url_list))
            self.set_current_progress(percent)
            yield self.current_progress_bar_percent_value
            time.sleep(random.uniform(15, 40))