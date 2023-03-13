cd /var/www

service apache2 start

# initialize the SQLite database
DB=/var/www/database/scrab.db
if [ ! -f "$DB" ]; then
    flask db init
    flask db migrate
    flask db upgrade
fi

sleep infinity
