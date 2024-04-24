# dharma

This is the newest code for the DHARMA project.

## Dependencies

The following Python packages need to be installed with `pip`:

	bs4
	flask
	PyICU
	requests
	saxonche
	websockets
	pegen

Note that the Python package for [ICU](https://icu.unicode.org/) is `PyICU`, not
`icu`! PyICU does not automatically install the libraries it needs to work, and
it wants all the ICU stuff to be installed, including the build tools, so you
need to install `libicu-dev` or `libicu-devel` (depending on the distribution),
not just `libicu`.

[`Pandoc`](https://pandoc.org) must also be installed, we use it at runtime
for rendering Markdown files.

##  Entry points

There are four main programs. On our server, they run concurrently and are
managed by `systemd`, but they can also be run manually, independently of
each other.

Firstly, we have a server program. It is used for read-only operations: display,
search, etc. It never writes to a database. The code's entry point is in
`server.py`. The server is thread-safe (or is supposed to be). It is possible to
run several server processes simultaneously, if the backend supports it.

Secondly, we have an update program. It is used for updating databases when
people push to git repositories or modify our Zotero bibliography. This is the
only program that modifies databases. The code's entry point is in `change.py`.
A single update process should run at a given time, not more. To update
databases, other processes communicate with this one through a named pipe.

Thirdly, we have a WebSocket client that is hooked to Zotero and that notifies
the update process whenever someone modifies the project's bibliography. The
code is in `zotero.py`.

Finally, we have a program for accessing zotero.org. The code is in
`zotero_proxy.py`. This is a server that is queried by XSLT files when they try
to access the bibliography. They make a lot of calls to the Zotero API, and
Zotero servers are often overloaded, thus we use a proxy that repeats API calls
on error, to prevent our builds from failing all the time.
