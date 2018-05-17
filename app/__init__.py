# -*- coding: utf-8 -*-

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user

app = Flask(__name__)
app.config.from_object('config')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
lm = LoginManager()
lm.init_app(app)
lm.login_view = 'login'
lm.login_message = 'Zaloguj się aby zobaczyć zawartość'

from app import models, views
from .models import User, SuggestedPrices

class MyModelView(ModelView):

    column_display_pk = True

    def is_accessible(self):
        return current_user.is_authenticated

admin = Admin(app, name='price_scraper', template_mode='bootstrap3')
admin.add_view(MyModelView(User, db.session))
admin.add_view(MyModelView(SuggestedPrices, db.session))