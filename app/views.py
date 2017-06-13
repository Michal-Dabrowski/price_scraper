from flask import render_template, flash, redirect, session, url_for, request, g, jsonify
from app import app, db
from .models import SuggestedPrices, Product, Dealer, DealerStatistics, ProductStatistics
from datetime import datetime
from config import PRODUCTS_PER_PAGE, UPLOAD_FOLDER
from .allegro_scraper import scrap_allegro, detect_name_and_suggested_price
from .ceneo_scraper import scrap_ceneo
from sqlalchemy import func
import json
from .forms import SearchForm
import random

@app.route('/')
@app.route('/start')
@app.route('/index')
def start():
    return render_template('start.html')

@app.route('/scraper/<source>', methods=['GET', 'POST'])
def scraper(source):
    form = SearchForm()
    if form.validate_on_submit():
        try:
            name = detect_name_and_suggested_price(form.search.data)
            name = name['name']
            products = Product.query.filter_by(product_name=name).order_by(Product.percentage_decrease.desc()).all()
            return render_template('products_list.html', products=products, dealer=name, source=source, form=form)
        except TypeError:
            flash('Nie znaleziono produktu ' + form.search.data)
            return render_template('scraper.html',
                           form=form,
                           source=source)
    return render_template('scraper.html',
                           form=form,
                           source=source)

@app.route('/old_analysis/<source>')
def old_analysis(source):
    subquery = db.session.query(func.count(Product.id).label('pc'), Product.dealer_id).filter_by(
        archive=False).filter_by(price_too_low=True).group_by(Product.dealer_id).order_by(
        func.count(Product.id)).subquery()
    query = db.session.query(Dealer).filter_by(source=source).outerjoin(subquery).order_by(subquery.c.pc.desc())
    dealers = query.all()
    winner = query.first()
    line_data = ProductStatistics.query.filter_by(source=source).order_by(ProductStatistics.timestamp.asc()).all()
    line_data = [[str(i.timestamp_short), i.good_auctions, i.bad_auctions, i.all_auctions] for i in line_data]
    return render_template('dealer_base.html',
                           source=source,
                           dealers=dealers,
                           winner=winner.name,
                           line_data=line_data
                           )

@app.route('/new_analysis/<source>')
def new_analysis(source):
    today = datetime.utcnow().strftime('%Y-%m-%d')
    newest_product = Product.query.filter_by(source=source).order_by(Product.timestamp_full.desc()).first()
    if newest_product is None or newest_product.timestamp_short != today:
            if source == 'allegro':
                data = scrap_allegro('brand_name')
            elif source == 'ceneo':
                data = scrap_ceneo('brand_name')
            data_dump = json.dumps(data)
            with open(UPLOAD_FOLDER + str(source) + '_dump_' + today + '.txt', 'w') as file:
                file.write(data_dump)
            update_product_database_from_object(data)
    else:
        flash('Ze względów bezpieczeństwa można wykonać tylko jedną analizę dziennie.')
    subquery = db.session.query(func.count(Product.id).label('pc'), Product.dealer_id).filter_by(
        archive=False).filter_by(price_too_low=True).group_by(Product.dealer_id).order_by(
        func.count(Product.id)).subquery()
    query = db.session.query(Dealer).filter_by(source=source).outerjoin(subquery).order_by(subquery.c.pc.desc())
    dealers = query.all()
    winner = query.first()
    line_data = ProductStatistics.query.filter_by(source=source).order_by(ProductStatistics.timestamp.asc()).all()
    line_data = [[str(i.timestamp_short), i.good_auctions, i.bad_auctions, i.all_auctions] for i in line_data]
    return render_template('dealer_base.html',
                           source=source,
                           dealers=dealers,
                           winner=winner.name,
                           line_data=line_data)

@app.route('/products_list/<source>/<dealer>')
def products_list(source, dealer):
    dealer = Dealer.query.filter_by(source=source).filter_by(name=dealer).first()
    products = dealer.show_bad_auctions()
    line_data = DealerStatistics.query.filter_by(dealer_id=dealer.dealer_id).order_by(DealerStatistics.timestamp.asc()).all()
    line_data = [[str(i.timestamp_short), i.good_auctions, i.bad_auctions, i.all_auctions] for i in line_data]
    return render_template('products_list.html',
                           source=source,
                           products=products,
                           dealer=dealer.name,
                           line_data=line_data
                           )

@app.route('/all_products_list/<source>/<dealer>')
def all_products_list(source, dealer):
    dealer = Dealer.query.filter_by(source=source).filter_by(name=dealer).first()
    products = dealer.products.filter_by(archive=False).order_by(Product.percentage_decrease.desc()).all()
    line_data = DealerStatistics.query.filter_by(dealer_id=dealer.dealer_id).order_by(DealerStatistics.timestamp.asc()).all()
    line_data = [[str(i.timestamp_short), i.good_auctions, i.bad_auctions, i.all_auctions] for i in line_data]
    return render_template('products_list.html',
                           source=source,
                           products=products,
                           dealer=dealer.name,
                           line_data=line_data
                           )

@app.route('/links/<source>/<dealer>')
def links(source, dealer):
    dealer = Dealer.query.filter_by(source=source).filter_by(name=dealer).first()
    products = dealer.show_bad_auctions()
    return render_template('links.html',
                           source=source,
                           dealer=dealer,
                           products=products)

@app.route('/<source>/top_10')
def top_10(source):
    products = db.session.query(
        Product.product_name, func.count(Product.product_name).label('products_count')).\
        filter_by(archive=False).filter_by(source=source).\
        group_by(Product.product_name).\
        order_by(func.count(Product.id).
                 desc()).all()
    return render_template('top_10.html',
                           dealer='TOP 10 zaniżonych produktów' + str(source),
                           products=products)

@app.route('/top_bad')
def top_bad():
    order_subquery = db.session.query(
        Product.dealer_id,
        func.count(Product.id).label('products_count')).\
        filter_by(archive=False).\
        filter_by(price_too_low=True).\
        group_by(Product.dealer_id).\
        order_by(func.count(Product.id).desc()).subquery()
    allegro_dealers = Dealer.query.filter_by(source='allegro').join(order_subquery).all()
    ceneo_dealers = Dealer.query.filter_by(source='ceneo').join(order_subquery).all()
    chart_data_a = [[i.name, i.count_bad_auctions()] for i in allegro_dealers]
    chart_data_a.insert(0, ['Sprzedawca', 'Zaniżone oferty'])
    chart_data_c = [[i.name, i.count_bad_auctions()] for i in ceneo_dealers]
    chart_data_c.insert(0, ['Sprzedawca', 'Zaniżone oferty'])
    return render_template('top_bad.html',
                           pie_data_a=chart_data_a[0:10], #top 10
                           pie_data_c=chart_data_c[0:10]  #top 10
                           )

@app.route('/interactive')
def interactive():
    return render_template('interactive.html')

@app.route('/background_process')
def background_process():
    try:
        lang = request.args.get('proglang', 0, type=str)
        if lang.lower() == 'python':
            return jsonify(result='You are wise')
        else:
            return jsonify(result='Try again.')
    except Exception as e:
        return str(e)

def update_statistics(source):
    today = datetime.utcnow().strftime('%Y-%m-%d')
    first_dealer_statistic = DealerStatistics.query.filter_by(source=source).order_by(DealerStatistics.timestamp.desc()).first()
    first_product_statistic = ProductStatistics.query.filter_by(source=source).order_by(ProductStatistics.timestamp.desc()).first()
    if first_dealer_statistic is None or first_dealer_statistic.timestamp_short != today:
        DealerStatistics.update_dealer_statistics(source)
    else:
        print('Dealer statistics not updated')
    if first_product_statistic is None or first_product_statistic.timestamp_short != today:
        ProductStatistics.update_product_statistics(source)
    else:
        print('Product statistics not updated')

def update_product_database_from_object(object):
    source = object[0]['source']
    old_products = db.session.query(Product).filter_by(source=source).all()
    for product in old_products:
        product.archive = True
        db.session.add(product)
    db.session.commit()

    for item in object:
        if item['suggested_price'] != 0:  # we don't want empty products

            product = Product.query.filter_by(source=source).filter_by(dealer_id=item['dealer_id']).filter_by(full_name=item['full_name']).first()
            if product is None:
                Dealer.add_dealer(item['dealer_id'], source, item['dealer_name'])
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
    update_statistics(source)