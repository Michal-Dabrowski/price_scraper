
import os
basedir = os.path.abspath(os.path.dirname(__file__))

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')
SQLALCHEMY_ECHO=False

WTF_CSRF_ENABLED = True
SECRET_KEY = r'\xd4@\xd9\xb2Ho\xcb\x83\xbet\xdb\x8d\xdf\r[\xd8\xf1\x87j\x1ah\x92\xae-'

# pagination
PRODUCTS_PER_PAGE = 10

UPLOAD_FOLDER = basedir + '\\app\\static\\files\\'
TEMPLATES_FOLDER = basedir + '\\app\\templates\\'
ALLOWED_EXTENSIONS = set(['csv'])