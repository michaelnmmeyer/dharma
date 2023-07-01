set -e

if test -z $WITHIN_DOCKER; then
	echo "Running docker" > /dev/stderr
	sudo docker run -t -i -p 8023:8023 \
		-v ~/programs/dharma/repos:/dharma/repos \
		-v ~/programs/dharma/dbs:/dharma/dbs dharma
else
	echo "Running python"
	python3 change.py &> repos/change.log &
	python3 server.py
fi
