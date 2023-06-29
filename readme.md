# dharma

This is the newest code for the dharma project.

The overall architecture is as simple as feasible. We use two main processes: a
server process and an update process.

The server process is mostly used for read-only operations: display, search,
etc. The code is in `server.py`. It is possible to run several server processes
at the same time (we allow reuse of the same socket, and SQLite takes care of
other IPC issues). The server is single-threaded, but could be made
multi-threaded without significant modifications. Running extra processes is
simpler anyway.

The update process is used for updating databases when people push to a
repository. The code is in `change.py`. A single update process should run at a
given time, not more. To keep things simple, we use a FIFO for IPC. The server
process writes to this FIFO the names of the repositories that have been
updated, one line per repository. The update process reads the repos names and
updates things accordingly. We do not implement any buffering for passing
messages, because pipe buffers are big enough for our purposes.
