#!/usr/bin/env bash

# Runs a web app instance (for production)
#
# Before using this script, clone the bare repo on the production server, and copy
# this script within it:
#
# 	git clone --bare https://github.com/michaelnmmeyer/dharma.git
#	cd dharma.git
#	wget https://raw.githubusercontent.com/michaelnmmeyer/dharma/master/run.sh
#
# Then, for starting a new web app instance, start a GNU screen session, and
# run the script from within it:
#
#	screen -S dharma
#	bash run.sh
#	# and detach: ^AD
#
# This runs the latest version of the code. It is possible to run several web
# app instances at the same time (we allow reuse of the same socket within the
# web app). It is also possible to run a specific revision of the web app by
# passing the git commit hash:
#
#	bash run.sh d4750e58394e3414d2782db1e9024f2b74cf9dc7
#
# The script works as follows. We create a git worktree for the revision given
# on the command-line, then create a new dummy file within it. Then we run the
# web app. Finally, after the web app has exited, we remove the dummy file we
# created and then try to delete the app worktree. The worktree is only
# actually deleted if all instances of the app have exited viz. if each dummy
# file has been deleted.

set -e

commit=$1
if test -z $commit; then
	commit=HEAD
fi
commit=$(git rev-parse --short $commit)
git fetch origin "*:*"
lock=""
here=$PWD

function cleanup() {
	cd $here
	rm -f $lock 2> /dev/null || true
	git worktree remove $commit 2> /dev/null || true
}
trap cleanup EXIT

if ! test -d $commit; then
	git worktree add --detach $commit $commit
fi
lock=$(mktemp -p $commit pid.$$.XXX)
cd $commit
HOST=beta screen -S $commit -d -m python3 server.py

cd $here
find -type f -name "pid.*" -not -path "./$commit/*" | \
	sed -En "s,.*pid\.([0-9]+).*,\1,p" | \
	while read pid; do
		echo "Killing $pid ($commit)" > /dev/stderr
		pkill -P $pid
	done
sleep infinity
