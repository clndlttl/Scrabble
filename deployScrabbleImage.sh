# usage: bash deployScrabbleImage.sh username@ip 

docker build -t scrabble-image:latest . || { echo "Build failed"; exit 1; }

docker save -o scrabble-image.tar scrabble-image:latest

if [ $# = 2 ]; then
    echo "rsync image with private key"
    rsync -rz -e "ssh -i '$2'" scrabble-image.tar runScrabble.sh $1:~
    ssh -i $2 $1
elif [ $# = 1 ]; then
    echo "scp image without private key"
    scp -C scrabble-image.tar runScrabble.sh $1:~
    ssh $1
fi