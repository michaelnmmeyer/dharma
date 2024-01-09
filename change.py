# To keep things simple, we use a FIFO for IPC. The server process is hooked to
# Github. Whenever a repository is updated, it writes to the FIFO the name of
# this repository, followed by a line break. On its side, the update process
# reads the repository names and updates things accordingly. We do not
# implement any buffering for passing messages, because pipe buffers are big
# enough for our purposes.

import os, sys, subprocess, time, json, select, errno, logging, fcntl
import argparse, traceback, collections
from dharma import config, validate, texts, biblio, catalog
from dharma.config import command

FIFO_ADDR = os.path.join(config.REPOS_DIR, "change.hid")

# Not all repos, only those that contain texts and other files we need.
REPOS = """
BESTOW
project-documentation
siddham
tfa-accalpuram-epigraphy
tfa-cempiyan-mahadevi-epigraphy
tfa-cirkali-epigraphy
tfa-kotumpalur-epigraphy
tfa-melappaluvur-kilappaluvur-epigraphy
tfa-pallava-epigraphy
tfa-pandya-epigraphy
tfa-sii-epigraphy
tfa-tamil-outside-TN-epigraphy
tfa-tamilnadu-epigraphy
tfa-tiruvavatuturai-TN-epigraphy
tfa-uttiramerur-epigraphy
tfb-arakan-epigraphy
tfb-badamicalukya-epigraphy
tfb-bengalcharters-epigraphy
tfb-bengalded-epigraphy
tfb-bhaumakara-epigraphy
tfb-daksinakosala-epigraphy
tfb-ec-epigraphy
tfb-eiad-epigraphy
tfb-gangaeast-epigraphy
tfb-kalyanacalukya-epigraphy
tfb-karnataka-epigraphy
tfb-licchavi-epigraphy
tfb-maitraka-epigraphy
tfb-parivrajaka-epigraphy
tfb-rastrakuta-epigraphy
tfb-sailodbhava-epigraphy
tfb-satavahana-epigraphy
tfb-somavamsin-epigraphy
tfb-telugu-epigraphy
tfb-vengicalukya-epigraphy
tfb-visnukundin-epigraphy
tfc-campa-epigraphy
tfc-khmer-epigraphy
tfc-nusantara-epigraphy
tfd-nusantara-philology
tfd-sanskrit-philology
""".strip().split()

TEXTS_DB = config.open_db("texts")

last_pull = 0
min_pull_wait = 5

# Github apparently doesn't like it when we pull too often. We often get a
# message "kex_exchange_identification: read: Connection reset by peer". So
# wait a bit between pulls.
def update_repo(name):
	global last_pull
	now = time.time()
	diff = now - last_pull
	if diff < min_pull_wait:
		time.sleep(min_pull_wait - diff)
	last_pull = now
	return command("git", "-C", os.path.join(config.REPOS_DIR, name), "pull", capture_output=False)

def latest_commit_in_repo(name):
	r = command("git", "-C", os.path.join(config.REPOS_DIR, name), "log", "-1", "--format=%H %at")
	hash, date = r.stdout.strip().split()
	date = int(date)
	return hash, date

class File:

	repo = None
	name = None
	path = None
	mtime = 0
	html = None
	status = None

	@property
	def data(self):
		with open(self.full_path) as f:
			return f.read()

	@property
	def owners(self):
		return texts.owners_of(self.full_path)

	@property
	def last_modified(self):
		return texts.last_mod_of(self.full_path)

	@property
	def full_path(self):
		return os.path.join(config.REPOS_DIR, self.repo, self.path)

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

	def check_db(self, db):
		if db.execute("select 1 from commits where repo = ? and commit_hash = ?",
			(self.repo, self.commit_hash)).fetchone():
			if db.execute("select 1 from texts where repo = ? and code_hash = ?",
				(self.repo, config.CODE_HASH)).fetchone():
				self.done = True
				return
			# The code changed, update everything (even possibly
			# deleted files, file matching rules might have
			# changed).
		else:
			(self.since,) = db.execute("select max(mtime) from files where repo = ?",
				(self.repo,)).fetchone() or (-1,)
		for (name,) in db.execute("select name from files where repo = ?", (self.repo,)):
			self.before.add(name)

	def check_repo(self):
		if self.done:
			return
		seen = set()
		repo_dir = os.path.join(config.REPOS_DIR, self.repo)
		for path in texts.iter_texts_in_repo(self.repo):
			name = os.path.basename(os.path.splitext(path)[0])
			if name in seen:
				continue # XXX how to complain? XXX cannot happen see iter_text_in_repo
			seen.add(name)
			mtime = int(os.stat(path).st_mtime)
			file = File()
			file.repo = self.repo
			file.name = os.path.splitext(name)[0]
			file.path = os.path.relpath(path, repo_dir)
			file.mtime = mtime
			if name not in self.before:
				self.insert.append(file)
			elif mtime > self.since:
				self.update.append(file)
			else:
				continue
			file.status = validate.status(path)
		for name in self.before:
			if name not in seen:
				self.delete.append(name)
		texts.gather_web_pages(self.insert + self.update)
		# Always process files in the same order.
		for group in ("insert", "update", "delete"):
			files = getattr(self, group)
			files.sort(key=lambda file: file.name)
		self.done = True

def update_db(repo):
	db = TEXTS_DB
	changes = Changes(repo)
	changes.check_db(db)
	if changes.done:
		return
	changes.check_repo()
	db.execute("insert or replace into commits(repo, commit_hash, commit_date) values(?, ?, ?)",
		(changes.repo, changes.commit_hash, changes.commit_date))
	for name in changes.delete:
		catalog.delete(name, db)
		db.execute("delete from owners where name = ?", (name,))
		db.execute("delete from texts where name = ?", (name,))
		db.execute("delete from files where repo = ? and name = ?", (changes.repo, name))
	for file in changes.insert + changes.update:
		db.execute("""insert or replace into files(name, repo, path, mtime, last_modified, data)
			values(?, ?, ?, ?, ?, ?)""",
			(file.name, file.repo, file.path, file.mtime, file.last_modified, file.data))
		db.execute("""insert or replace into texts(
			name, repo, html_path, code_hash, status)
			values(?, ?, ?, ?, ?)""",
			(file.name, file.repo, file.html, config.CODE_HASH, file.status))
		for git_name in file.owners:
			db.execute("insert or ignore into owners(name, git_name) values(?, ?)",
				(file.name, git_name))
		catalog.insert(file, db)

def backup_to_jawakuno():
	command("bash", "-x", config.path_of("backup_to_jawakuno.sh"), capture_output=False)

@TEXTS_DB.transaction
def handle_changes(name):
	db = TEXTS_DB
	db.execute("begin immediate")
	update_repo(name)
	update_db(name)
	db.execute("replace into metadata values('last_updated', strftime('%s', 'now'))")
	db.execute("commit")
	if name == "tfd-nusantara-philology":
		backup_to_jawakuno()

def clone_all():
	for name in REPOS:
		path = os.path.join(config.REPOS_DIR, name)
		try:
			os.rmdir(path)
		except FileNotFoundError:
			pass
		except OSError as e:
			if e.errno == errno.ENOTEMPTY:
				continue
			raise
		command("git", "clone", f"git@github.com:erc-dharma/{name}.git", path,
			capture_output=False)

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
		if name == "all":
			logging.info("updating everything...")
			for name in REPOS:
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
		elif name in REPOS:
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
		os.mkdir(config.REPOS_DIR)
	except FileExistsError:
		pass
	clone_all()
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
	parser.add_argument("-k", "--skip-update", action="store_true")
	args = parser.parse_args()
	if args.skip_update:
		NEXT_FULL_UPDATE += FORCE_UPDATE_DELTA
	main()
