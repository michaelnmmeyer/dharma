set -e errexit
set -o pipefail

bib_dir=repos/bibliography

if ! test -d $bib_dir; then
	git clone git@github.com:erc-dharma/bibliography.git $bib_dir
fi
git -C $bib_dir pull

sqlite3 -noheader dbs/texts.sqlite "select json from biblio_data order by key" > $bib_dir/data.jsonl.tmp
mv $bib_dir/data.jsonl.tmp $bib_dir/data.jsonl

git -C $bib_dir add data.jsonl
if ! git -C $bib_dir diff-index --quiet HEAD; then
	git -C $bib_dir commit -m "Backup bibliography"
	git -C $bib_dir push
fi
