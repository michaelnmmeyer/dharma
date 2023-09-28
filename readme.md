# dharma

This is the newest code for the DHARMA project.

## Running the application

To install and run it, you need, at a minimum, docker, git, and make. Clone this
repository into `~/`. Make sure you have admin access to the dharma
repositories on github, and copy your private SSH key to `~/dharma/ssh_key`. Then
build the container with:

	make image

Copy the dharma databases (not available yet!) into `~/dharma/dbs`. Finally, run
the container with:

	bash run.sh

You can then open http://localhost:8023 to look at the website.

##  Basic architecture

The overall architecture is as simple as feasible. We store our data in a few
SQLite databases, and use two main processes: a server process and an update
process.

The server process is used for read-only operations: display, search, etc. It
never writes to a database, at the exception of the Github log database, which
is used for debugging. The code's entry point is in `server.py`. It is possible
to run several server processes at the same time (we allow reuse of the same
socket, and SQLite takes care of other IPC issues). However, the server code is
*not* thread-safe. Running extra processes is simpler anyway.

The update process is used for updating databases when people push to git
repositories. The code's entry point is in `change.py`. A single update process
should run at a given time, not more.

We use the WAL mode in SQLite. Thus, writers don't block readers and
vice-versa, but writers do block each other, which is why use just one and
serialize writes.

## Gotchas

If `git push` are too frequent, it is theoretically possible that the update
process might not keep up and thus miss updates. Nothing prevents this from
happening for now. In the meantime, you can manually trigger a full update of
the databases by running the script `change.py` and then the following in
another terminal:

	echo all > ~/dharma/repos/change.hid
