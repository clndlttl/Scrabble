mkdir -p database
rm -rf database/*

docker build -t scrabble-image .

docker run --name scrabble-cont \
           --mount type=bind,source=$(pwd)/database/,target=/var/www/database \
           -p 80:80 \
           -d scrabble-image

sleep 2

docker ps
