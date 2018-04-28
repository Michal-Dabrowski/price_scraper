import scrapy
import json
from config import BRAND_NAME


class AllegroScraper(scrapy.Spider):
    name = 'AllegroScraper'
    start_urls = [
        'https://allegro.pl/listing?string={}&order=m&bmatch=base-relevance-floki-5-nga-hc-ele-1-2-0901&p=0'.format(BRAND_NAME)
    ]

    def parse(self, response):
        """
        Allegro keeps products in a json object in
        "window.__listing_ItemsStoreState" variable in <script> in their HTML code

        :param response:
        :return:
        """
        selectors = response.xpath("//*[contains(text(), 'window.__listing_ItemsStoreState')]")
        for selector in selectors:
            products_json = selector.re('window.__listing_ItemsStoreState = (.*);')
            products_json = json.loads(products_json[0])
            yield products_json