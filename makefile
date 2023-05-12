all:

update-repos:
	git stash -m for_submodules
	git submodule update --remote
	git add repos
	git commit -m 'Update submodules' || true
	git stash pop $$(git stash list | grep for_submodules | grep -o '^[^:]+')

.PHONY: all update-repos
