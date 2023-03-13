import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    SECRET_KEY = 'catalyzing-a-cleaner-future'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, '../database/scrab.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
