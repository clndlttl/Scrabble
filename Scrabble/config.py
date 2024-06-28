import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    SECRET_KEY = 'ashitloadofpoints'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, '../database/scrab.db')
    REDIS_URL = 'redis://'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
