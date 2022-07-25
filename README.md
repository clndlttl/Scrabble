Clone this repo to your home directory:
- cd ~
- git clone <url>

Start a super-user session:
- sudo su

Install webserver and database:
- apt update
- apt install apache2
- apt-get install libapache2-mod-wsgi-py3
- apt install mysql-server
- apt-get install python3-mysqldb

Create the database for scrabble:
- sudo mysql -u root -p
- mysql> create database scrab;
- mysql> create user 'scrab-user'@'localhost' identified by 'scrab-pw';
- mysql> grant all privileges on scrab.* to 'scrab-user'@'localhost';
- mysql> quit

Install python3 dependencies automatically:
- pip3 install --upgrade pip
- pip3 install -r /home/<yourname>/cogscrabble/requirements.txt

Install python3 dependencies manually, if the above fails:
- pip3 install --upgrade pip
- pip3 install requests
- pip3 install Flask
- pip3 install Flask-WTF
- pip3 install flask-migrate
- pip3 install flask-sqlalchemy 
- pip3 install flask-login
- pip3 install email-validator
- pip3 install flask-mail
- pip3 install pyjwt
- pip3 install python-dotenv

Create the .env file in your home directory:
- touch /home/<yourname>/.env
