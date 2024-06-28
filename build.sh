mkdir -p database
mkdir -p logs
rm -rf logs/*

docker build -t scrabble-image .

docker run --name scrabble-cont \
           --mount type=bind,source=$(pwd)/database/,target=/var/www/database \
           --mount type=bind,source=$(pwd)/logs/,target=/var/www/database \
           -p 80:80 \
           -d scrabble-image

sleep 2

docker ps
