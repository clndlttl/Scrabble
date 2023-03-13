mkdir -p database

docker build -t scrab-image .

docker run --name scrab-cont \
	   --mount type=bind,source=$(pwd)/database/,target=/var/www/database \
	   -p 80:80 \
	   -d scrab-image

docker ps

