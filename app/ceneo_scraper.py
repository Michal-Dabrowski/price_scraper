# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import requests
import re
import time
import random
from app.allegro_scraper import Product, detect_name_and_suggested_price, count_percentage_decrease

def scrap_ceneo(brand_name):
    analysis_list = list()
    main_page = True
    page_number = 1
    last_page = 1
    product_dict_list = []
    filtered_dict = {}
    headers = requests.utils.default_headers()
    headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:52.0) Gecko/20100101 Firefox/52.0'})

    while page_number <= last_page:
        if main_page:
            response = requests.get('http://www.ceneo.pl/;szukaj-' + str(brand_name), headers=headers)
            soup = BeautifulSoup(response.content)
            last_page = detect_last_page(soup)
            last_page -= 1
            main_page = False
            product_dict_list.append(collect_products_names_and_links(soup))
        else:
            response = requests.get('http://www.ceneo.pl/;szukaj-' + str(brand_name) + ';0020-30-0-0-' + str(page_number) + '.htm', headers=headers)
            soup = BeautifulSoup(response.content)
            page_number += 1
            product_dict_list.append(collect_products_names_and_links(soup))
        print("Scraping page {} from {}".format(page_number, last_page + 1))
        time.sleep(random.uniform(15, 35))
    print('All links collected, now we will scrap all of them (may take a while).')

    for product_dict in product_dict_list:
        for key, value in product_dict.items():
            product_name = key
            product_url = value
            name_and_suggested_price = detect_name_and_suggested_price(product_name)
            if name_and_suggested_price is not None:
                filtered_dict[product_name] = product_url

    link_number = 1
    for key, value in filtered_dict.items():
        product_url = value
        products_list = get_dealers_and_prices_from_ceneo_product_page(product_url)
        analysis_list += products_list
        time.sleep(random.uniform(15, 40))
        print("Scraping link {} from {}".format(link_number, len(filtered_dict)))
        link_number += 1

    return analysis_list

def collect_products_names_and_links(soup):
    links = dict()

    products = soup.find_all('div', class_='cat-prod-row-desc')
    for product in products:
        product = product.find_all('a', class_=" js_conv")
        for element in product:
            product = element.text
            link = element.get('href')
            links[str(product)] = str(link)
    return links

def detect_last_page(soup):
    try:
        last_page = soup.find('div', class_="pagination-top")
        last_page = last_page.text
        last_page = int(re.search(r'\d+', last_page).group())
    except:
        print("Couldn't find the last page! Setting the last page to '20'.")
        last_page = 20  # we probably don't need more... probably
    return last_page

def get_dealers_and_prices_from_ceneo_product_page(url):
    headers = requests.utils.default_headers()
    headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:52.0) Gecko/20100101 Firefox/52.0'})
    response = requests.get('http://www.ceneo.pl/' + url, headers=headers)
    soup = BeautifulSoup(response.content)

    promoted_products_table = soup.find_all('table', class_="product-offers js_product-offers")
    regular_products_table = soup.find_all('table', class_="product-offers js_product-offers js_normal-offers ")
    promoted_products_list = analyze_products_from_result_set(promoted_products_table, url)
    regular_products_list = analyze_products_from_result_set(regular_products_table, url)
    return promoted_products_list + regular_products_list

def analyze_products_from_result_set(result_set, url):
    products_list = []
    for element in result_set:
        products = element.find_all('tr', class_="product-offer js_product-offer")
        for item in products:
            try:
                product = Product()
                product.source = 'ceneo'
                product.dealer_name = item.get('data-shopurl')
                product.price = float(item.get('data-offer-price'))
                product.dealer_id = item.get('data-shop')
                product.full_name = item.find('span', class_="short-name__txt").text
                product.url = 'http://www.ceneo.pl' + url
                product.new = True
                name_and_suggested_price = detect_name_and_suggested_price(product.full_name)  # generates None for discontinued products
                product.suggested_price = float(name_and_suggested_price['suggested_price'].replace(',', '.'))
                product.product_name = name_and_suggested_price['name']
                product.price_too_low = product.price < product.suggested_price
                product.percentage_decrease = count_percentage_decrease(product.suggested_price, product.price)
            except TypeError:  # 'NoneType' object is not subscriptable
                pass
            products_list.append(product.__dict__)
    return products_list