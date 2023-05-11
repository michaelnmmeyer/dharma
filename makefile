all:

update-repos:
	git stash
	git submodule update --remote
	git add repos
	git commit -m 'Update submodules'
	git stash pop

.PHONY: all update-repos
