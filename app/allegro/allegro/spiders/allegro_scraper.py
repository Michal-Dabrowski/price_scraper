import scrapy
import json
from config import BRAND_NAME

class AllegroScraper(scrapy.Spider):
    name = 'allegro'
    start_urls = [
        'https://allegro.pl/listing?string={}&order=m&bmatch=base-relevance-floki-5-nga-hc-ele-1-2-0901&p=0'.format(BRAND_NAME)
    ]
    custom_settings = {
        'ROBOTSTXT_OBEY': False,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:52.0) Gecko/20100101 Firefox/52.0',
        'DOWNLOAD_DELAY': 5.0,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1
    }

    def parse(self, response):
        """
        Allegro keeps products in a json object in
        "window.__listing_ItemsStoreState" variable in <script> in their HTML code

        :param response:
        :return:
        """
        number_of_pages = response.xpath(".//div[@class='layout__actions']//li[@class='quantity']//text()").extract_first()
        number_of_pages = int(number_of_pages)

        products_selector = response.xpath("//*[contains(text(), 'window.__listing_ItemsStoreState')]")[0]
        products_json = products_selector.re('window.__listing_ItemsStoreState = (.*);')
        products_json = json.loads(products_json[0])

        for group in products_json['itemsGroups']:
            for item in group['items']:
                yield {
                    'type': self.get_type(item),
                    'full_name': self.get_name(item),
                    'source': 'allegro',
                    'url': self.get_url(item),
                    'price': self.get_price(item),
                    'dealer_id': self.get_dealer_id(item),
                    'free_shipping': self.free_shipping(item),
                    'shipping_costs': self.get_shipping_costs(item),
                    'new': self.is_product_new(item),
                    'archive': self.is_archived(item)
                }

        for page in range(number_of_pages + 1):
            next_page = 'https://allegro.pl/listing?string={}&order=m&bmatch=base-relevance-floki-5-nga-hc-ele-1-2-0901&p={}'.format(BRAND_NAME, page)
            yield response.follow(next_page, self.parse)

    def get_type(self, product):
        return product['type']

    def is_product_new(self, product):
        try:
            return product['attributes'][0]['value'] == 'Nowy'
        except (KeyError, IndexError):
            return False

    def free_shipping(self, product):
        try:
            return product['deliveryInfo'][0]['name'] == 'freeDelivery'
        except (KeyError, IndexError):
            return False

    def get_shipping_costs(self, product):
        try:
            return product['deliveryInfo'][0]['price']['amount']
        except (KeyError, IndexError):
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
