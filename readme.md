# dharma

This is the newest code for the DHARMA project.

## Installation

The following Python packages need to be installed with `pip`:

	flask
	PyICU
	requests
	saxonche
	websockets

`PyICU` wants all the ICU stuff to be installed, so install `libicu-dev` or
`libicu-devel`, depending on the distribution.

##  Basic architecture

The overall architecture is as simple as feasible. We store our data in a few
SQLite databases, and use two main processes: a server process and an update
process.

The server process is used for read-only operations: display, search, etc. It
never writes to a database. The code's entry point is in `server.py`. The
server is thread-safe.

The update process is used for updating databases when people push to git
repositories or modify our Zotero bibliography. The code's entry point is in
`change.py`. A single update process should run at a given time, not more.

We use the WAL mode in SQLite. Thus, writers don't block readers and vice-versa,
but writers do block each other, which is why we use just one and serialize
writes.

In addition to the above, we run a WebSocket client that is hooked to Zotero
and that notifies the update process whenever someone modifies the project's
bibliography. The code is in `zotero.py`.

There is a final entry point, `zotero_proxy.py`. This is a separate server
that is queried by XSLT files when they try to access the bibliography. They
make a lot of calls to the Zotero API, and Zotero servers are often overloaded,
thus we use an intermediary to prevent our builds to fail all the time.
