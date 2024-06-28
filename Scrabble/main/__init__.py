from flask import Blueprint

bp = Blueprint('main', __name__)

from Scrabble.main import routes