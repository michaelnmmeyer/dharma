all:

update-texts:
	rm -f texts/*
	python3 texts.py update
	for f in texts/*.xml; do \
		python3 xmlformat.py $$f > tmp && mv tmp $$f; \
	done
	git add texts
	git commit -m "Update texts"

image:
	git rev-parse HEAD > version.txt
	sudo docker build -t dharma .

upload: image
	sudo docker save dharma > dharma.tar
	sudo chown michael dharma.tar
	rsync --progress --no-whole-file --compress --compress-choice=zstd --inplace dharma.tar beta:

.PHONY: all update-texts image upload

inscriptions.rnc: $(wildcard texts/DHARMA_INS*.xml)
	java -jar validation/trang.jar $^ $@

global.rnc: $(wildcard texts/DHARMA_*.xml)
	java -jar validation/trang.jar $^ $@

%.rng: %.rnc
	java -jar validation/trang.jar $^ $@
