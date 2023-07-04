all:

update-texts:
	rm -f texts/*
	sqlite3 dbs/texts.sqlite "select printf('repos/%s/%s', repo, xml_path) \
		from texts natural join latest_commits natural join validation \
		where valid order by name" | while read f; do \
			python3 xmlformat.py $$f > texts/$$(basename $$f); \
		done
	git add texts
	git commit -m "Update texts"

image:
	git rev-parse HEAD > version.txt
	sudo docker build -t dharma .

.PHONY: all update-texts image

inscription.rnc: $(wildcard texts/DHARMA_INS*.xml)
	java -jar validation/trang.jar $^ $@

diplomatic.rnc: $(wildcard texts/DHARMA_DiplEd*.xml)
	java -jar validation/trang.jar $^ $@

critical.rnc: $(wildcard texts/DHARMA_CritEd*.xml)
	java -jar validation/trang.jar $^ $@

global.rnc: $(wildcard texts/DHARMA_*.xml)
	java -jar validation/trang.jar $^ $@

%.rng: %.rnc
	java -jar validation/trang.jar $^ $@
