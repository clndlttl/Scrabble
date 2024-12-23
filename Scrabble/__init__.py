from flask import Flask
from Scrabble.config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from redis import Redis
from rq import Queue

import logging
from logging.handlers import RotatingFileHandler
import time

formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
formatter.converter = time.gmtime

app_logger = logging.getLogger('app_logger')
app_logger.setLevel(logging.DEBUG)
app_handler = RotatingFileHandler('logs/app.log', maxBytes=100000, backupCount=10)
app_handler.setFormatter(formatter)
app_logger.addHandler(app_handler)

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'main.login'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    app.logger = app_logger

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    
    app.logger.debug('register blueprint')
    from Scrabble.main import bp as main_bp
    app.register_blueprint(main_bp)

    app.redis = Redis(host='localhost', port=6379, decode_responses=True)
    app.task_queue = Queue('scrabble-queue', connection=app.redis)

    return app

from Scrabble import models