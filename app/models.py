# -*- coding: utf-8 -*-

from app import db
import pandas as pd
from config import UPLOAD_FOLDER
from datetime import datetime
import time
import requests
import json
import re

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(64), unique=True)
    password = db.Column(db.String(64))
    email = db.Column(db.String(64), unique=True)
    active = db.Column(db.Boolean)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

class Dealer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dealer_id = db.Column(db.Integer, unique=True)
    name = db.Column(db.String(64), index=True, unique=True)
    source = db.Column(db.String(16))

    products = db.relationship('Product', backref='seller', lazy='dynamic')
    statistics = db.relationship('DealerStatistics', backref='seller', lazy='dynamic')

    def count_bad_auctions(self):
        return self.products.filter_by(archive=False).filter_by(price_too_low=True).count()

    def show_bad_auctions(self):
        return self.products.filter_by(archive=False).filter_by(price_too_low=True).order_by(Product.percentage_decrease.asc()).all()

    def count_auctions(self):
        return self.products.filter_by(archive=False).count()

class SuggestedPrices(db.Model):
    product_name = db.Column(db.String(360), index=True, primary_key=True, unique=True)
    product_name_regex_pattern = db.Column(db.String(360))
    suggested_price = db.Column(db.Integer)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(16))
    dealer_id = db.Column(db.Integer, db.ForeignKey('dealer.dealer_id'))
    full_name = db.Column(db.String(360), index=True)
    url = db.Column(db.String(500), index=True)
    price = db.Column(db.Integer, index=True)
    free_shipping = db.Column(db.Boolean)
    product_name = db.Column(db.String(360), db.ForeignKey('suggested_prices.product_name'))
    price_too_low = db.Column(db.Boolean)
    percentage_decrease = db.Column(db.Integer)
    timestamp_full = db.Column(db.DateTime)
    timestamp_short = db.Column(db.String(360))
    suggested_price = db.Column(db.Integer, index=True)
    archive = db.Column(db.Boolean)

class DealerStatistics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(16))
    dealer_id = db.Column(db.Integer(), db.ForeignKey('dealer.dealer_id'))
    bad_auctions = db.Column(db.Integer())
    good_auctions = db.Column(db.Integer())
    all_auctions = db.Column(db.Integer())
    timestamp_short = db.Column(db.String(10))
    timestamp = db.Column(db.DateTime)

class ProductStatistics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(16))
    bad_auctions = db.Column(db.Integer())
    good_auctions = db.Column(db.Integer())
    all_auctions = db.Column(db.Integer())
    timestamp_short = db.Column(db.String(10), unique=True)
    timestamp = db.Column(db.DateTime)


def add_dealer(dealer_id, source, name):
    d = Dealer.query.filter_by(dealer_id=dealer_id).first()
    if d is None:
        if source == 'allegro':
            name = detect_allegro_dealer_name(dealer_id)
        dealer = Dealer(dealer_id=dealer_id, name=name, source=source)
        print('Adding dealer {}'.format(name))
        db.session.add(dealer)
        db.session.commit()
        time.sleep(2)

def detect_allegro_dealer_name(seller_id):
    url = "https://allegro.pl/listing-user-data/users/" + str(seller_id)
    headers = requests.utils.default_headers()
    headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:52.0) Gecko/20100101 Firefox/52.0'})
    response = requests.get(url=url, headers=headers)
    response = response.content
    response = response.decode('utf-8')
    json_object = json.loads(response)
    return json_object['login']

def populate_table_from_file(filename):
    """
    Accepts csv file with names and suggested prices.
    File should be located in static\files.
    Names should be column 1, prices column 5 (index starts from 0).
    """
    file = pd.read_csv(UPLOAD_FOLDER + '\\' + filename, sep=',', header=None)
    names_raw = file[1].tolist()
    suggested_prices = file[5].tolist()
    replace_pairs = [("\\", ""), ('-', '-?\s?'), ('"', '"?'), (' ', '\s?')]
    for index, name in enumerate(names_raw):
        name = name.lower()
        name = name.strip()
        original_name = name
        for item in replace_pairs:
            name = name.replace(item[0], item[1])
        suggested_price = SuggestedPrices(product_name=original_name,
                                          product_name_regex_pattern=name,
                                          suggested_price=suggested_prices[index]
                                          )
        db.session.add(suggested_price)
    db.session.commit()

def update_dealer_statistics(source):
    dealers = Dealer.query.filter_by(source=source).all()
    timestamp_short = datetime.utcnow().strftime('%Y-%m-%d')
    timestamp = datetime.utcnow()
    for dealer in dealers:
        products_query = dealer.products.filter_by(source=source).filter_by(timestamp_short=timestamp_short).filter_by(archive=False)
        bad_auctions = products_query.filter_by(price_too_low=True).count()
        good_auctions = products_query.filter_by(price_too_low=False).count()
        all_auctions = products_query.count()
        s = DealerStatistics(dealer_id=dealer.dealer_id,
                             bad_auctions=bad_auctions,
                             good_auctions=good_auctions,
                             all_auctions=all_auctions,
                             timestamp_short=timestamp_short,
                             timestamp=timestamp,
                             source=source
                             )
        db.session.add(s)
    db.session.commit()


def update_product_statistics(source):
    timestamp = datetime.utcnow()
    timestamp_short = datetime.utcnow().strftime('%Y-%m-%d')
    product_query = Product.query.filter_by(source=source).filter_by(timestamp_short=timestamp_short).filter_by(archive=False)

    bad_auctions = product_query.filter_by(price_too_low=True).count()
    good_auctions = product_query.filter_by(price_too_low=False).count()
    all_auctions = product_query.count()

    s = ProductStatistics(bad_auctions=bad_auctions,
                              good_auctions=good_auctions,
                              all_auctions=all_auctions,
                              timestamp_short=timestamp_short,
                              timestamp=timestamp,
                              source=source
                              )
    db.session.add(s)
    db.session.commit()

def detect_name_and_suggested_price(name):
    """
    :param name: string consisting product name
    :return: name and price from SuggestedPrices table from database
    """
    name = name.lower()

    for element in ['pokrywa', 'kufer', 'case', 'igła', 'headshell', 'decksaver', 'cable', 'kabel', 'statyw', 'laptop',
                    'stand', 'puck', 'adapter', 'szczoteczka', 'ear pack', 'fader cap', 'knob cap', 'pasek', 'adaptor',
                    'gooseneck', 'stylus']:
        if element in name:
            return None

    suggested_prices_sql_table = SuggestedPrices.query.all()
    for row in suggested_prices_sql_table:
        match = re.search(row.product_name_regex_pattern, name)
        if match:
            return {'name': row.product_name, 'suggested_price': row.suggested_price}
    return None