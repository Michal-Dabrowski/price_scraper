# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html


from datetime import datetime
from app.models import detect_name_and_suggested_price, count_percentage_decrease, db, Product, add_dealer


class AllegroPipeline(object):
    def process_item(self, item, spider):
        name_and_price = detect_name_and_suggested_price(item['full_name'])
        item['product_name'] = name_and_price['name']
        item['suggested_price'] = name_and_price['suggested_price']
        item['percentage_decrease'] = count_percentage_decrease(item['suggested_price'], item['price'])
        item['price_too_low'] = item['price'] < item['suggested_price']

        source = item['source']

        product = Product.query.filter_by(source=source).filter_by(dealer_id=item['dealer_id']).filter_by(
            full_name=item['full_name']).first()

        if product is None:
            add_dealer(item['dealer_id'], source, item['dealer_name'])
            product = Product(dealer_id=item['dealer_id'],
                              source=source,
                              full_name=item['full_name'],
                              url=item['url'],
                              price=item['price'],
                              free_shipping=item['free_shipping'],
                              product_name=item['product_name'],
                              price_too_low=item['price_too_low'],
                              percentage_decrease=item['percentage_decrease'],
                              suggested_price=item['suggested_price'],
                              timestamp_full=datetime.utcnow(),
                              timestamp_short=datetime.utcnow().strftime('%Y-%m-%d'),
                              archive=False
                              )
            db.session.add(product)
        else:
            product.url = item['url']
            product.price = item['price']
            product.free_shipping = item['free_shipping']
            product.price_too_low = item['price_too_low']
            product.suggested_price = item['suggested_price']
            product.percentage_decrease = item['percentage_decrease']
            product.timestamp_full = datetime.utcnow()
            product.timestamp_short = datetime.utcnow().strftime('%Y-%m-%d')
            product.archive = False
            db.session.add(product)
        db.session.commit()

        return item
