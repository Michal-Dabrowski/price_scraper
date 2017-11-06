
import os
basedir = os.path.abspath(os.path.dirname(__file__))

BRAND_NAME = ''

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')
SQLALCHEMY_ECHO=False

WTF_CSRF_ENABLED = True
SECRET_KEY = 'you-will-never-guess'

# pagination
DEALERS_PER_PAGE = 10

UPLOAD_FOLDER = basedir + '/app/static/files/'
TEMPLATES_FOLDER = basedir + '/app/templates/'
ALLOWED_EXTENSIONS = set(['csv'])