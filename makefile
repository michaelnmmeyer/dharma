all:

validate:
	rm -f texts/*
	python3 texts.py update
	python3 validate.py

.PHONY: all validate

inscriptions.rnc: $(wildcard texts/DHARMA_INS*.xml)
	java -jar validation/trang.jar $^ $@

global.rnc: $(wildcard texts/DHARMA_*.xml)
	java -jar validation/trang.jar $^ $@

%.rng: %.rnc
	java -jar validation/trang.jar $^ $@
