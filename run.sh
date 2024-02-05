#!/usr/bin/env bash

# Run this from within screen. But huma-num apparently kills user sessions and thus screen.
# To prevent this, do:
#
#     sudo loginctl enable-linger $USER
#
# Then run screen with:
#
#     systemd-run --scope --user screen

set -e

if test -z "$WITHIN_DOCKER"; then
	echo "Running docker" > /dev/stderr
	sudo docker run -t -i -p 127.0.0.1:8023:8023 \
		-v ~/dharma/repos:/dharma/repos \
		-v ~/dharma/dbs:/dharma/dbs \
		-v ~/dharma/logs:/dharma/logs \
		dharma
else
	echo "Running python" > /dev/stderr
	python3 change.py &> logs/change.log &
	python3 zotero.py &> logs/zotero.log &
	python3 server.py
fi
