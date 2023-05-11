all:

update-repos:
	git submodule update --remote
	git stash
	git add repos
	git commit -m 'Update submodules'
	git stash pop

.PHONY: all update-repos
