# dharma

This is the newest code for the DHARMA project.

## Running the application

To install and run it, you need, at a minimum, docker (the package name is
`docker.io` in Debian), git, and make. Clone this repository into `~/`:

	cd ~
	git clone https://github.com/michaelnmmeyer/dharma.git

Make sure you have admin access to the dharma repositories on github, and copy
the private SSH key you're using for github to `~/dharma/ssh_key`. Then build
the container with:

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
repositories or modify our Zotero bibliography. The code's entry point is in
`change.py`. A single update process should run at a given time, not more.

In addition to the above, we run a WebSocket client that is hooked to Zotero
and that notifies the update process whenever someone modifies the project's
bibliography. The code is in `zotero.py`.

We use the WAL mode in SQLite. Thus, writers don't block readers and
vice-versa, but writers do block each other, which is why we use just one and
serialize writes.
