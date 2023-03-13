FROM ubuntu

RUN apt-get update

RUN apt-get install -y python3-pip python3-dev
RUN apt-get install -y apache2
RUN apt-get install -y libapache2-mod-wsgi-py3
RUN apt-get install -y vim

RUN pip install --upgrade pip
RUN pip install Flask
RUN pip install Flask-WTF
RUN pip install flask-migrate
RUN pip install flask-sqlalchemy
RUN pip install flask-login
RUN pip install requests

COPY scrabble.conf /etc/apache2/sites-available/
RUN a2dissite 000-default
RUN a2ensite scrabble

WORKDIR /var/www

COPY Scrabble Scrabble
COPY wsgi.py entrypoint.sh ./

RUN mkdir -p Scrabble/database

EXPOSE 80

ENTRYPOINT ["bash","/var/www/entrypoint.sh"]
