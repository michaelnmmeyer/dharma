# git names

The file `git_names.tsv` maps git user names to DHARMA members id. By "git user
name", I mean the names displayed when you run `git log --format=%aN`. Most
people don't provide a readable user name, and some people use several names,
so the point is to make it clear who commits what and to be able to know which
file is edited by whom.

The file contains two columns. The first one is a git user name, the second one
is a DHARMA member id viz. a four-letter code.
