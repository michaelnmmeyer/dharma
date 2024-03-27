set -e errexit

cd repos
if ! test -d jawakuno; then
	git clone git@github.com:arlogriffiths/jawakuno.git
fi
cd jawakuno
git pull

inp_dir="$DHARMA_HOME/repos/tfd-nusantara-philology/output/critical-edition/texts"
out_dir=texts/txt/tfd-nusantara-philology
rsync --progress --archive --delete-after "$inp_dir/" $out_dir
git add .
if ! git diff-index --quiet HEAD; then
	git commit -m "Update texts from tfd-nusantara-philology"
	git push
fi
