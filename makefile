all:

update-repos:
	git stash -m for_submodules
	git submodule update --remote
	git add repos
	git commit -m 'Update submodules' || true
	git stash pop `git stash list | grep for_submodules | grep -o '^[^:]+'` || true

update-texts:
	python3 texts.py
	for f in texts/*.xml; do \
		python3 xmlformat.py $$f > tmp && mv tmp $$f; \
	done

.PHONY: all update-repos update-texts
