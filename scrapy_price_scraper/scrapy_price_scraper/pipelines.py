# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

from app.models import detect_name_and_suggested_price, count_percentage_decrease


class AllegroPipeline(object):
    def process_item(self, item, spider):
        try:
            name_and_price = detect_name_and_suggested_price(item['full_name'])
            item['product_name'] = name_and_price['name']
            item['suggested_price'] = name_and_price['suggested_price']
            item['percentage_decrease'] = count_percentage_decrease(item['suggested_price'], item['price'])
            item['price_too_low'] = item['price'] < item['suggested_price']
        except TypeError:
            pass
        return item
