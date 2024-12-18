FROM ubuntu

RUN apt update

WORKDIR /var/www

RUN apt install -y vim
RUN apt install -y nginx
RUN apt install -y supervisor
RUN apt install -y python3-pip python3-venv python3-dev

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip
RUN pip install Flask
RUN pip install Flask-WTF
RUN pip install flask-migrate
RUN pip install flask-sqlalchemy
RUN pip install flask-login
RUN pip install gunicorn 
RUN pip install requests
RUN pip install pytz

# nginx
RUN rm /etc/nginx/sites-enabled/default
COPY deployment/scrabble.conf /etc/nginx/sites-available/
RUN ln -s /etc/nginx/sites-available/scrabble.conf /etc/nginx/sites-enabled/
RUN service nginx reload

# supervisor
COPY deployment/gunicorn.conf /etc/supervisor/conf.d/

COPY Scrabble Scrabble
COPY wsgi.py entrypoint.sh ./

EXPOSE 80

ENTRYPOINT ["bash","/var/www/entrypoint.sh"]
