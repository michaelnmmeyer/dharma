schemas = $(addprefix schemas/,inscription bestow critical diplomatic prosody)

all: $(addsuffix .rng,$(schemas))

update-repos:
	for d in repos/*; do \
		test -d $$d && git -C $$d pull; \
	done

update-texts: update-repos
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
	for d in repos/*; do \
		test -d $$d || continue; \
		test -n "`git status -s`" || continue; \
		git -C $$d add --all; \
		git -C $$d commit -m "$(m)"; \
		git -C $$d push; \
	done

deploy-schemas: $(addsuffix .xml,$(schemas)) $(addsuffix .rng,$(schemas))
	cp schemas/inscription.xml repos/project-documentation/schema/DHARMA_INSSchema_v01.xml
	cp schemas/bestow.xml repos/project-documentation/schema/DHARMA_BESTOW_v01.xml
	cp schemas/critical.xml repos/project-documentation/schema/DHARMA_CritEdSchema_v02.xml
	cp schemas/diplomatic.xml repos/project-documentation/schema/DHARMA_DiplEDSchema_v01.xml
	cp schemas/prosody.xml repos/project-documentation/schema/DHARMA_ProsodySchema_v01.xml
	cp schemas/inscription.rng repos/project-documentation/schema/latest/DHARMA_Schema.rng
	cp schemas/bestow.rng repos/project-documentation/schema/latest/DHARMA_BESTOW.rng
	cp schemas/critical.rng repos/project-documentation/schema/latest/DHARMA_CritEdSchema.rng
	cp schemas/diplomatic.rng repos/project-documentation/schema/latest/DHARMA_DiplEDSchema.rng
	cp schemas/prosody.rng repos/project-documentation/schema/latest/DHARMA_ProsodySchema.rng
	git -C repos/project-documentation commit -am "Schema update"
	git -C repos/project-documentation push

.PHONY: all update-repos update-texts download-dbs list-texts forever image commit-all deploy-schemas

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

%.rnc: %.rng
	java -jar jars/trang.jar $^ $@

%.rng: %.xml
	curl -F fileToConvert=@$^ https://teigarage.tei-c.org/ege-webservice/Conversions/ODD%3Atext%3Axml/ODDC%3Atext%3Axml/relaxng%3Aapplication%3Axml-relaxng > tmp && mv tmp $@
