all:

update-texts:
	for d in repos/*; do \
		test -d $$d && git -C $$d pull; \
	done
	mkdir texts || true
	rm -f texts/*
	rsync --progress 'beta:dharma/dbs/texts.sqlite*' dbs/
	sqlite3 dbs/texts.sqlite "select printf('../repos/%s/%s', repo, xml_path) \
		from texts" | while read f; do \
		ln -s $$f texts/$$(basename $$f); \
	done

download-dbs:
	rsync --progress 'beta:dharma/dbs/*.sqlite*' dbs/

list-texts:
	@sqlite3 dbs/texts.sqlite "select printf('repos/%s/%s', repo, path) \
		from texts natural join files order by name"

# Use like this: make forever cmd="echo hello"
forever:
	@while inotifywait -qqre modify . @dbs @docs @notes @past @repos; do \
		$(cmd) || true; \
	done

image:
	git pull
	git rev-parse HEAD > version.txt
	git show --no-patch --format=%at HEAD >> version.txt
	sudo docker build -t dharma .

# Use like this: make commit-all m="Commit message"
commit-all:
	@for d in repos/*; do \
		test -d $$d || continue; \
		test -n "`git status -s`" || continue; \
		git -C $$d add --all; \
		git -C $$d commit -m "$(m)"; \
		git -C $$d push; \
	done


.PHONY: all update-texts download-dbs list-texts forever image commit-all

inscription.rnc: $(wildcard texts/DHARMA_INS*.xml)
	java -jar validation/trang.jar $^ $@

diplomatic.rnc: $(wildcard texts/DHARMA_DiplEd*.xml)
	java -jar validation/trang.jar $^ $@

critical_translation.rnc: $(wildcard texts/DHARMA_CritEd*_trans*.xml)
	java -jar validation/trang.jar $^ $@

critical_edition.rnc: $(filter-out $(wildcard texts/DHARMA_CritEd*_trans*.xml),$(wildcard texts/DHARMA_CritEd*.xml))
	java -jar validation/trang.jar $^ $@

global.rnc: $(wildcard texts/DHARMA_*.xml)
	java -jar validation/trang.jar $^ $@

%.rng: %.rnc
	java -jar validation/trang.jar $^ $@
