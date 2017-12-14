# -*- coding: utf-8 -*-

from flask import render_template, flash, redirect, session, url_for, request, g, jsonify, send_file, Response, stream_with_context, send_from_directory
from app import app, db, lm
from .models import Product, Dealer, DealerStatistics, ProductStatistics, User
from datetime import datetime
from config import DEALERS_PER_PAGE, UPLOAD_FOLDER, BRAND_NAME
from .allegro_scraper import AllegroScraper
from .ceneo_scraper import CeneoScraper, CeneoUrlScraper
from .pagination_object import Pagination
from sqlalchemy import func
from .models import update_product_statistics, update_dealer_statistics, add_dealer, detect_name_and_suggested_price, count_percentage_decrease
import json
from .forms import SearchForm, LoginForm, RegisterForm
from flask_login import login_user, logout_user, current_user, login_required
from passlib.hash import sha256_crypt
from math import ceil
import random
import time

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        login = form.login.data
        password = form.password.data
        registered_user = User.query.filter_by(login=login, active=True).first()
        if registered_user is None:
            flash('Nieprawidłowy login lub hasło')
            return redirect(url_for('login'))
        elif sha256_crypt.verify(password, registered_user.password):
            login_user(registered_user)
            return redirect(url_for('old_analysis', source='allegro', page=1))
        else:
            flash('Nieprawidłowy login lub hasło')
            return redirect(url_for('login'))
    return render_template('login.html', form=form)

@app.route('/register', methods= ['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        register_user(form.login.data, form.password.data, form.email.data)
        flash('Rejestracja pomyślna. Poczkaj na aktywację konta przez administratora strony.')
        return(redirect(url_for('login')))
    return render_template("register.html",
                           title="Register",
                           form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@login_required
@app.route('/scraper/<source>', methods=['GET', 'POST'])
def scraper(source='allegro'):
    return render_template('scraper.html',
                           source=source)

@app.route('/')
@app.route('/start')
@app.route('/index')
@app.route('/old_analysis/<source>')
@app.route('/old_analysis/<source>/<int:page>')
@login_required
def old_analysis(source='allegro', page=1):
    subquery = db.session.query(func.count(Product.id).label('pc'), Product.dealer_id).filter_by(
        archive=False).filter_by(price_too_low=True).group_by(Product.dealer_id).order_by(
        func.count(Product.id)).subquery()
    query = db.session.query(Dealer).filter_by(source=source).outerjoin(subquery).order_by(subquery.c.pc.desc())
    pagination = Pagination(page, 10, query.count())
    dealers = query.paginate(page, 10, error_out=False).items
    line_data = ProductStatistics.query.filter_by(source=source).order_by(ProductStatistics.timestamp.asc()).all()
    line_data = [[str(i.timestamp_short), i.good_auctions, i.bad_auctions, i.all_auctions] for i in line_data]
    return render_template('dealer_base.html',
                           source=source,
                           dealers=dealers,
                           line_data=line_data,
                           page=page,
                           pagination=pagination
                           )

@app.route('/scrap/<source>/<force>')
@login_required
def scrap(source, force):
    def generate_progress():
        today = datetime.utcnow().strftime('%Y-%m-%d')
        newest_product = Product.query.filter_by(source=source).order_by(Product.timestamp_full.desc()).first()
        if newest_product is None or newest_product.timestamp_short != today or force=='true':
            if source == 'allegro':
                g.scraper = AllegroScraper(BRAND_NAME)
                for step in g.scraper.generator():
                    yield "data:" + str(step) + "\n\n"
            elif source == 'ceneo':
                g.url_scraper = CeneoUrlScraper(BRAND_NAME)
                for step in g.url_scraper.generator():
                    yield "data:" + str(step) + " url" + "\n\n"
                g.scraper = CeneoScraper(g.url_scraper.filtered_url_list)
                for step in g.scraper.generator():
                    yield "data:" + str(step) + "\n\n"
            dump_json_to_file(g.scraper.products_list, source, today)
            update_product_database_from_object(g.scraper.products_list)
            update_statistics(source)
            yield "data:done\n\n"
        else:
            yield "data:error\n\n"
    resp = Response(stream_with_context(generate_progress()), mimetype='text/event-stream')
    resp.headers['X-Accel-Buffering'] = 'no'
    return resp

@app.route('/products_list/<source>/<dealer>')
@login_required
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
@login_required
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
@login_required
def links(source, dealer):
    dealer = Dealer.query.filter_by(source=source).filter_by(name=dealer).first()
    products = dealer.show_bad_auctions()
    return render_template('links.html',
                           source=source,
                           dealer=dealer,
                           products=products)

@app.route('/<source>/top_10')
@login_required
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
@login_required
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

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search_navbar():
    if not g.search_form.validate_on_submit():
        return redirect(url_for('index'))
    else:
        try:
            name = detect_name_and_suggested_price(g.search_form.search.data)
            name = name['name']
            products = Product.query.filter_by(product_name=name).filter_by(archive=False).order_by(Product.percentage_decrease.asc()).all()
            return render_template('products_list.html', products=products, dealer=name, search=True)
        except TypeError:
            flash('Nie znaleziono produktu ' + g.search_form.search.data)
            return render_template('products_list.html', products=[], dealer=str(g.search_form.search.data))

@app.before_request
def before_request():
    g.user = current_user
    g.search_form = SearchForm()

@lm.user_loader
def load_user(id):
    return User.query.get(int(id))

def url_for_other_page(page):
    args = request.view_args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args)
app.jinja_env.globals['url_for_other_page'] = url_for_other_page

def block_scraper(source):
    print('using block scraper')
    today = datetime.utcnow().strftime('%Y-%m-%d')
    newest_product = Product.query.filter_by(source=source).order_by(Product.timestamp_full.desc()).first()
    if newest_product is None or newest_product.timestamp_short != today:
        return True
    return False

def dump_json_to_file(data, source, today):
    data_dump = json.dumps(data)
    with open(UPLOAD_FOLDER + str(source) + '_dump_' + today + '.txt', 'w') as file:
        file.write(data_dump)
    print('Dump file saved.')

def register_user(login, password, email):
    user = User(login=login, password=sha256_crypt.encrypt(password), email=email, active=False)
    db.session.add(user)
    db.session.commit()

def update_statistics(source):
    today = datetime.utcnow().strftime('%Y-%m-%d')
    first_dealer_statistic = DealerStatistics.query.filter_by(source=source).order_by(DealerStatistics.timestamp.desc()).first()
    first_product_statistic = ProductStatistics.query.filter_by(source=source).order_by(ProductStatistics.timestamp.desc()).first()
    if first_dealer_statistic is None or first_dealer_statistic.timestamp_short != today:
        update_dealer_statistics(source)
        print('Dealer statistics updated')
    else:
        print('Dealer statistics not updated')
    if first_product_statistic is None or first_product_statistic.timestamp_short != today:
        update_product_statistics(source)
        print('Product statistics updated')
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
        if item['product_name'] is not None:  # we don't want empty products

            product = Product.query.filter_by(source=source).filter_by(dealer_id=item['dealer_id']).filter_by(full_name=item['full_name']).first()
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
    print('Database updated.')

def update_product_database_from_file(filename):
    with open(UPLOAD_FOLDER + filename) as file:
        data = json.loads(file.read())
        update_product_database_from_object(data)