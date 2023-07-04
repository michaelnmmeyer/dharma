for repo in repos/*; do
	test -d $repo || continue;
	git -C $repo log --format='%aN|%ae'
done | sort -u
