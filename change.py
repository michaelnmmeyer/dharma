# To keep things simple, we use a FIFO for IPC. The server process is hooked to
# Github. Whenever a repository is updated, it writes to the FIFO the name of
# this repository, followed by a line break. On its side, the update process
# reads the repository names and updates things accordingly. We do not
# implement any buffering for passing messages, because pipe buffers are big
# enough for our purposes.

import os, sys, subprocess, time, select, errno, logging, fcntl
import argparse, traceback, collections
from dharma import config, validate, texts, biblio, catalog, people, langs
from dharma import gaiji, prosody, repos

FIFO_ADDR = config.path_of("change.hid")

db = config.db("texts")

# Timestamp of the last git pull/clone
last_pull = 0

# Wait this long between two pulls, counting in seconds
min_pull_wait = 10

def all_useful_repos():
	# Always process repos in the same order.
	ret = db.execute("""select repo from repos
		where textual or repo = 'project-documentation'
		order by repo""")
	return [name for (name,) in ret]

def clone_repo(name):
	path = config.path_of("repos", name)
	# The simplest way to determine if we already have cloned the repo is
	# to check if we have a non-empty directory at the expected location.
	try:
		os.rmdir(path)
	except FileNotFoundError:
		pass
	except OSError as e:
		if e.errno == errno.ENOTEMPTY:
			return False
		raise
	config.command("git", "clone", f"git@github.com:erc-dharma/{name}.git",
		path, capture_output=False)
	return True

# Github apparently doesn't like it when we pull too often. We often get a
# message "kex_exchange_identification: read: Connection reset by peer". So we
# wait a bit between pulls.
def update_repo(name):
	global last_pull
	now = time.time()
	diff = now - last_pull
	if diff < min_pull_wait:
		time.sleep(min_pull_wait - diff)
	last_pull = now
	# Attempt to clone the repo, in case we don't have it. Otherwise pull.
	if clone_repo(name):
		return
	return config.command("git", "-C", config.path_of("repos", name),
		"pull", capture_output=False)

def latest_commit_in_repo(name):
	r = config.command("git", "-C", config.path_of("repos", name),
		"log", "-1", "--format=%H %at")
	hash, date = r.stdout.strip().split()
	date = int(date)
	return hash, date

class Changes:

	def __init__(self, repo):
		self.repo = repo
		self.since = -1
		self.done = False
		self.before = set()
		self.insert = []
		self.update = []
		self.delete = []
		self.commit_hash, self.commit_date = latest_commit_in_repo(self.repo)

	def check_db(self):
		commit_hash, code_hash = db.execute("""
			select commit_hash, code_hash
			from repos where repo = ?""",
			(self.repo,)).fetchone() or (None, None)
		if commit_hash == self.commit_hash:
			if code_hash == config.CODE_HASH:
				self.done = True
				return
			# The code changed, we need to update everything
			# (even possibly deleted files, file matching rules
			# might have changed).
		else:
			# Need to update all files that have been modified
			# since the last commit viz. files that have been
			# modified more recently than the newest file seen
			# so far in this repo.
			(self.since,) = db.execute("""select max(mtime)
				from files where repo = ?""",
				(self.repo,)).fetchone() or (-1,)
		for (name,) in db.execute("""select name from files
			where repo = ?""", (self.repo,)):
			self.before.add(name)

	def check_repo(self):
		if self.done:
			return
		seen = set()
		for file in texts.iter_texts_in_repo(self.repo):
			seen.add(file.name)
			if file.name not in self.before:
				self.insert.append(file)
			elif file.mtime > self.since:
				self.update.append(file)
			else:
				continue
			setattr(file, "_status", validate.status(file))
		for name in self.before:
			if name not in seen:
				self.delete.append(name)
		texts.gather_web_pages(self.repo, self.insert + self.update)
		# Always process files in the same order, for reproductibility.
		self.insert.sort(key=lambda file: file.name)
		self.update.sort(key=lambda file: file.name)
		self.delete.sort()
		self.done = True

def update_db(repo):
	changes = Changes(repo)
	changes.check_db()
	if changes.done:
		return
	changes.check_repo()
	db.execute("""update repos
		set commit_hash = ?, commit_date = ?, code_hash = ?
		where repo = ?""",
		(changes.commit_hash, changes.commit_date, config.CODE_HASH, changes.repo))
	for name in changes.delete:
		catalog.delete(name)
		db.execute("delete from owners where name = ?", (name,))
		db.execute("delete from files where name = ?", (name,))
	for file in changes.insert + changes.update:
		db.execute("""
			insert or replace into files(
				name, repo, path, mtime,
				last_modified_commit, last_modified, data)
			values(?, ?, ?, ?, ?, ?, ?)""",
			(file.name, file.repo, file.path, file.mtime, *file.last_modified, file.data))
		for git_name in file.owners:
			db.execute("""
				insert or ignore into owners(name, git_name)
				values(?, ?)""", (file.name, git_name))
		catalog.insert(file)

# We should always put stuff like names, etc. in the db instead of keeping it
# in-memory, so that we can tell what's the current data just by looking at
# the db. Otherwise would have to write introspection code. Other reason: at
# some point, we want to have a downloadable read-only db.
def update_project():
	# XXX add a test to verify whether the files we need changed, to avoid
	# doing a full rebuild when not necessary.
	people.make_db()
	langs.make_db()
	gaiji.make_db()
	prosody.make_db()
	# XXX what about schemas and docs? run make? this should be built as
	# part of project-documentation, and we should not store schemas in
	# the app repo.
	# TODO store needed files from project-documentation in the db, otherwise
	# we're gonna get stuck later on
	catalog.rebuild()
	repo = "project-documentation"
	commit_hash, commit_date = latest_commit_in_repo(repo)
	db.execute("""update repos
		set commit_hash = ?, commit_date = ?, code_hash = ?
		where repo = ?""",
		(commit_hash, commit_date, config.CODE_HASH, repo))

# Request from Arlo.
def backup_to_jawakuno():
	config.command("bash", "-x", config.path_of("backup_to_jawakuno.sh"),
		capture_output=False)

@config.transaction("texts")
def handle_changes(name):
	db.execute("begin")
	update_repo(name)
	if name == "project-documentation":
		update_project()
	else:
		update_db(name)
	db.execute("replace into metadata values('last_updated', strftime('%s', 'now'))")
	db.execute("commit")
	if name == "tfd-nusantara-philology":
		backup_to_jawakuno()

# Must be at least this big in POSIX. Linux currently has 4096.
PIPE_BUF = 512

# When we should force a full update. We perform one at startup.
NEXT_FULL_UPDATE = time.time()

# Force a full update every FORCE_UPDATE_DELTA seconds.
FORCE_UPDATE_DELTA = 1 * 60 * 60

# In the worst case, if we're not fast enough to handle any update events, we
# just end up running forced full updates continuously. We check if a full
# update is necessary *before* trying to update a singular repo, so there is
# always an opportunity for all repos to be updated.
def read_names(fd):
	buf = ""
	global NEXT_FULL_UPDATE
	while True:
		now = time.time()
		wait = NEXT_FULL_UPDATE - now
		if wait <= 0:
			logging.info("forcing full update")
			yield "all"
			wait = FORCE_UPDATE_DELTA
			NEXT_FULL_UPDATE = now + wait
			continue
		end = buf.find("\n")
		if end >= 0:
			name = buf[:end]
			yield name
			buf = buf[end + 1:]
			continue
		logging.info("selecting")
		rlist, _, _ = select.select([fd], [], [], wait)
		if not rlist:
			continue
		data = os.read(fd, PIPE_BUF)
		logging.info("read %d" % len(data))
		buf += data.decode("ascii")

def read_changes(fd):
	for name in read_names(fd):
		repos = all_useful_repos()
		if name == "all":
			logging.info("updating everything...")
			for name in repos:
				logging.info("updating %r" % name)
				handle_changes(name)
				logging.info("updated %r" % name)
			logging.info("updating biblio...")
			biblio.update()
			logging.info("updated biblio")
			logging.info("updated everything")
		elif name == "bib":
			logging.info("updating biblio...")
			biblio.update()
			logging.info("updated biblio")
		elif name in repos:
			logging.info("updating single repo %r..." % name)
			handle_changes(name)
			logging.info("updated single repo %r" % name)
		else:
			logging.warning("junk command: %r" % name)

# To be used by clients, not when running this __main__ (this would release the
# lock we hold on the fifo).
def notify(name):
	msg = name.encode("ascii") + b"\n"
	assert len(msg) <= PIPE_BUF
	fd = os.open(FIFO_ADDR, os.O_RDWR | os.O_NONBLOCK)
	try:
		os.write(fd, msg)
	finally:
		os.close(fd)

def run():
	try:
		os.mkdir(config.path_of("repos"))
	except FileExistsError:
		pass
	try:
		os.mkfifo(FIFO_ADDR)
	except FileExistsError:
		pass
	fd = os.open(FIFO_ADDR, os.O_RDWR)
	try:
		fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
	except OSError as e:
		logging.error("cannot obtain lock, is another change process running?")
		sys.exit(1)
	logging.info("ready")
	try:
		read_changes(fd)
	finally:
		os.close(fd)

def main():
	while True:
		try:
			run()
		except KeyboardInterrupt:
			break
		except Exception as e:
			logging.error(e)
			traceback.print_exception(e)
			# Don't immediately retry to avoid a busy loop. Might
			# want to distinguish network errors from programming
			# errors, etc.; in the first case, we could retry
			# sooner.
			global NEXT_FULL_UPDATE
			now = time.time()
			if NEXT_FULL_UPDATE - now < 0:
				NEXT_FULL_UPDATE += FORCE_UPDATE_DELTA

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("-k", "--skip-update", action="store_true", help="""
		do not force an update at startup""")
	args = parser.parse_args()
	if args.skip_update:
		NEXT_FULL_UPDATE += FORCE_UPDATE_DELTA
	main()
