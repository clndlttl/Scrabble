
docker load -i scrabble-image.tar

docker rm -f scrabble-cont || true

mkdir -p scrabble/logs
rm -f scrabble/logs/*
mkdir -p scrabble/database

if [ "$1" = "new" ]; then
    echo "Purging database!"
    rm -rf scrabble/database/*
fi

docker run --name scrabble-cont \
           --mount type=bind,source=$(pwd)/scrabble/logs/,target=/var/www/logs \
           --mount type=bind,source=$(pwd)/scrabble/database/,target=/var/www/database \
           -p 80:80 \
           -d --restart unless-stopped scrabble-image

docker ps

echo "\n Scrabble is running!"