schemas = $(addprefix schemas/,inscription bestow critical diplomatic prosody tei-epidoc)

generated_tei = \
	$(addsuffix .rng,$(schemas)) \
	$(addsuffix .html,$(schemas)) \
	$(addsuffix .oddc,$(schemas)) \
	$(addsuffix .sch,$(schemas))
generated_views = $(patsubst %.md,%.tpl,$(wildcard views/*.md))

all: $(generated_tei) $(generated_views)

clean:
	rm -f $(generated_tei) $(generated_views)

update-repos:
	for d in repos/*; do \
		test -d $$d && git -C $$d pull; \
	done

update-texts: update-repos
	mkdir texts || true
	rm -f texts/*
	rsync --progress 'dharma:dharma/dbs/texts.sqlite*' dbs/
	sqlite3 dbs/texts.sqlite "select printf('../repos/%s/%s', repo, path) \
		from texts natural join files" | while read f; do \
		ln -s $$f texts/$$(basename $$f); \
	done

download-dbs:
	rsync --progress 'dharma:dharma/dbs/*.sqlite*' dbs/

list-texts:
	@sqlite3 dbs/texts.sqlite "select printf('repos/%s/%s', repo, path) \
		from texts natural join files order by name"

ARLO_PLAIN=repos/jawakuno/texts/txt/prasasti/DHARMA_export
arlo-plain:
	python3 parse_ins.py && \
		rm -rf $(ARLO_PLAIN) && \
		mv plain $(ARLO_PLAIN) && \
		git -C repos/jawakuno commit -am "Update DHARMA inscriptions" && \
		git -C repos/jawakuno push

# Ussage: make forever cmd="echo hello"
cmd := $(MAKE) -j3
forever:
	@$(cmd) || true
	@while inotifywait -qqre modify . @dbs @docs @notes @past @repos @schemas; do \
		$(cmd) || true; \
	done

version.txt:
	git rev-parse HEAD > version.txt
	git show --no-patch --format=%at HEAD >> version.txt

image:
	git pull
	$(MAKE) version.txt
	sudo docker build -t dharma .

# Usage: make commit-all m="Commit message"
m := "Address encoding problems"
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
	git -C repos/project-documentation commit -am "Schema update" && git -C repos/project-documentation push

.PHONY: all clean update-repos update-texts download-dbs list-texts forever version.txt image commit-all deploy-schemas

views/%.tpl: views/%.md
	pandoc -f markdown -t html $^ -o $@

trang := java -jar jars/trang.jar

inscription.rnc: $(wildcard texts/DHARMA_INS*.xml)
	$(trang) $^ $@

diplomatic.rnc: $(wildcard texts/DHARMA_DiplEd*.xml)
	$(trang) $^ $@

critical_translation.rnc: $(wildcard texts/DHARMA_CritEd*_trans*.xml)
	$(trang) $^ $@

critical_edition.rnc: $(filter-out $(wildcard texts/DHARMA_CritEd*_trans*.xml),$(wildcard texts/DHARMA_CritEd*.xml))
	$(trang) $^ $@

global.rnc: $(wildcard texts/DHARMA_*.xml)
	$(trang) $^ $@

%.rnc: %.rng
	$(trang) $^ $@

%.rng: %.oddc
	python3 xslt.py tei/odds/odd2relax.xsl $^ > $@
	# curl -F fileToConvert=@$^ https://teigarage.tei-c.org/ege-webservice/Conversions/ODD%3Atext%3Axml/ODDC%3Atext%3Axml/relaxng%3Aapplication%3Axml-relaxng > $@

%.sch: %.oddc
	# See readme.txt in schematron dir for details on the build process.
	# First extract schematron rules
	# curl -F fileToConvert=@$^ https://teigarage.tei-c.org/ege-webservice/Conversions/ODD%3Atext%3Axml/ODDC%3Atext%3Axml/isosch%3Atext%3Axml > $@.stage0
	python3 xslt.py tei/odds/extract-isosch.xsl $^ > $@.stage0
	# Compile the XSLT script
	# We can ignore the stage1 transformation with iso_dsdl_include.xsl.
	# In the following, -versionmsg:off is to suppress the warning
	# "Running an XSLT 1 stylesheet with an XSLT 2 processor"
	# java -jar jars/saxon9.jar -versionmsg:off -s:$@.stage0schematron/iso_abstract_expand.xsl -xsl:schematron/iso_abstract_expand.xsl -o:$@.stage2
	python3 xslt.py schematron/iso_abstract_expand.xsl $@.stage0 > $@.stage2
	rm $@.stage0
	# java -jar jars/saxon9.jar -versionmsg:off -s:$@.stage2 -xsl:schematron/iso_svrl_for_xslt2.xsl -o:$@
	python3 xslt.py schematron/iso_svrl_for_xslt2.xsl $@.stage2 > $@
	rm $@.stage2
	# For validating with sch, do java -jar jars/saxon9.jar -xsl:schemas/inscription.sch -s:texts/DHARMA_INSVengiCalukya00015.xml
	# And look at the nodes //svrl:successful-report

%.html: %.oddc
	# curl -F fileToConvert=@$^ https://teigarage.tei-c.org/ege-webservice/Conversions/ODDC%3Atext%3Axml/oddhtml%3Aapplication%3Axhtml%2Bxml > $@
	python3 xslt.py tei/odds/odd2html.xsl $^ > $@

# Expansion of ODD files is necessary for all other transforms
%.oddc: %.xml
	# curl -F fileToConvert=@$^ https://teigarage.tei-c.org/ege-webservice/Conversions/ODD%3Atext%3Axml/ODDC%3Atext%3Axml > $@
	python3 xslt.py tei/odds/odd2odd.xsl $^ > $@
