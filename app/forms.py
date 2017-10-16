# -*- coding: utf-8 -*-

from flask_wtf import FlaskForm, Form
from wtforms import StringField, BooleanField, PasswordField
from wtforms.validators import DataRequired, EqualTo
from .models import User

class SearchForm(FlaskForm):
    search = StringField('search')

class LoginForm(FlaskForm):
    login = StringField('login', validators=[DataRequired()])
    password = PasswordField('password', validators=[DataRequired()])

class RegisterForm(Form):
    password = PasswordField('password',
                             validators=[DataRequired(),
                                         EqualTo('confirm', message="Hasła muszą być takie same!")
                                         ]
                             )
    confirm = PasswordField("Potwierdź hasło")
    login = StringField('login', validators=[DataRequired()])
    email = StringField('email', validators=[DataRequired()])

    def validate(self):
        if not Form.validate(self):
            return False

        if User.query.filter_by(login=self.login.data).first() is not None:
            self.login.errors.append('Login zajęty')
            return False

        if User.query.filter_by(email=self.email.data).first() is not None:
            self.email.errors.append('Email zajęty')
        return True