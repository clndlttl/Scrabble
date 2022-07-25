import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '../../.env'))

class Config(object):
    SECRET_KEY = 'to-protect-and-serve-vision'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:///' + os.path.join(basedir, '../../scrab.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ADMINS = os.environ.get('ADMINS') or ['fakeusername@gmail.com']
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.googlemail.com'
    MAIL_PORT = os.environ.get('MAIL_PORT') or 587
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') or 1
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'fakeusername'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or 'fakepassword'
