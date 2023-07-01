all:

update-texts:
	rm -f texts/*
	python3 texts.py update
	for f in texts/*.xml; do \
		python3 xmlformat.py $$f > tmp && mv tmp $$f; \
	done
	git add texts
	git commit -m "Update texts"

.PHONY: all update-texts

inscriptions.rnc: $(wildcard texts/DHARMA_INS*.xml)
	java -jar validation/trang.jar $^ $@

global.rnc: $(wildcard texts/DHARMA_*.xml)
	java -jar validation/trang.jar $^ $@

%.rng: %.rnc
	java -jar validation/trang.jar $^ $@
