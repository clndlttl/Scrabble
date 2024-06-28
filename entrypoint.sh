cd /var/www

# start redis
service redis-server start

# start nginx and supervisor (gunicorn, rq workers) 
service nginx start
service supervisor start

# create the migrations folder if it doesn't exist, but it should!
if [ ! -d /var/www/migrations ]; then
    flask db init
fi
#flask db stamp head
flask db migrate
flask db upgrade

sleep infinity
