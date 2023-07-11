#!/usr/bin/env bash

set -o errexit
set -o pipefail

test -n "$DHARMA_HOME"
cd "$DHARMA_HOME"

dbs_dir=$DHARMA_HOME/dbs

tmp_dir=$(mktemp -d)
trap "rm -rf $tmp_dir" EXIT

mkdir $tmp_dir/dbs
for db in $dbs_dir/*.sqlite; do
	name=$(basename $db)
	sql=".backup ""'""$tmp_dir/dbs/$name""'"""
	sqlite3 $db "$sql"
done
archive=dharma_$(date -uIseconds).tar.gz
tar --force-local -C $tmp_dir -czvf $tmp_dir/$archive dbs
scp $tmp_dir/$archive gamma:dharma
