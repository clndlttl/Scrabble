import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    SECRET_KEY = 'ashitloadofpoints'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, '../database/scrab.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CSS_DIR = os.path.join(basedir, 'static/css')
    REDIS_URL = 'redis://'
