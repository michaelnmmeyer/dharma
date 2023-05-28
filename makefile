all:

update-repos:
	git stash -m for_submodules
	git submodule update --remote
	git add repos
	git commit -m 'Update submodules' || true
	git stash pop `git stash list | grep for_submodules | grep -o '^[^:]+'` || true

update-texts:
	python3 texts.py update
	for f in texts/*.xml; do \
		python3 xmlformat.py $$f > tmp && mv tmp $$f; \
	done

inscriptions.rnc: $(wildcard texts/DHARMA_INS*.xml)
	java -jar validation/trang.jar $^ $@

global.rnc: $(wildcard texts/DHARMA_*.xml)
	java -jar validation/trang.jar $^ $@

.PHONY: all update-repos update-texts
