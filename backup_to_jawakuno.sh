set -e errexit

test -n "$DHARMA_HOME"

cd "$DHARMA_HOME/repos/jawakuno"
git pull

inp_dir=$DHARMA_HOME/repos/tfd-nusantara-philology/output/critical-edition/texts
out_dir=texts/txt/tfd-nusantara-philology

rsync --progress --archive --delete-after "$inp_dir/" $out_dir
git add $out_dir
git commit -m "Update texts from tfd-nusantara-philology" || true
git push
