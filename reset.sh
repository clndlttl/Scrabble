rm ../scrab.db
rm -rf ./migrations
rm -rf ./__pycache__
rm -rf ./Scrabble/__pycache__
flask db init
flask db migrate
flask db upgrade
