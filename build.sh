echo Stopping and removing container...
docker stop scrabble-cont && docker container rm scrabble-cont

mkdir -p database
mkdir -p logs

chmod -R 777 database
chmod -R 777 logs

rm -rf logs/*

if [ "$1" = "new" ]; then
    echo "Purging database!!!"
    rm -rf database/*
fi

echo Building image...
docker build -t scrabble-image .

echo Running image...
docker run --name scrabble-cont \
           --mount type=bind,source=$(pwd)/database/,target=/var/www/database \
           --mount type=bind,source=$(pwd)/logs/,target=/var/www/logs \
           -p 80:80 \
           -d scrabble-image

sleep 1

docker ps
