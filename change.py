# To keep things simple, we use a FIFO for IPC. The server process is hooked to
# Github. Whenever a repository is updated, it writes to the FIFO the name of
# this repository, followed by a line break. On its side, the update process
# reads the repository names and updates things accordingly. We do not
# implement any buffering for passing messages, because pipe buffers are big
# enough for our purposes.

import os, sys, subprocess, time, json, select, errno, logging, fcntl, argparse, traceback
from dharma import config, validate, texts, biblio, grapheme, catalog
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
tfa-tamilnadu-epigraphy
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
tfb-licchavi-epigraphy
tfb-maitraka-epigraphy
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

def update_repo(name):
	return command("git", "-C", os.path.join(config.REPOS_DIR, name), "pull", capture_output=False)

def latest_commit_in_repo(name):
	r = command("git", "-C", os.path.join(config.REPOS_DIR, name), "log", "-1", "--format=%H %at")
	hash, date = r.stdout.strip().split()
	date = int(date)
	return hash, date

def update_db(conn, name):
	commit_hash, date = latest_commit_in_repo(name)
	if conn.execute("select 1 from commits where repo = ? and commit_hash = ?",
		(name, commit_hash)).fetchone():
		if conn.execute("select 1 from validation where repo = ? and code_hash = ?",
			(name, config.CODE_HASH)).fetchone():
			# No need to revalidate
			return
	conn.execute("insert or replace into commits(repo, commit_hash, commit_date) values(?, ?, ?)",
		(name, commit_hash, date))
	schema_errs = validate.validate_repo(name)
	unicode_errs = grapheme.validate_repo(name)
	state = {}
	for file in schema_errs:
		state[file] = {
			"schema": schema_errs[file],
			"unicode": unicode_errs[file],
		}
	repo_dir = os.path.join(config.REPOS_DIR, name)
	conn.execute("delete from validation where repo = ?", (name,))
	conn.execute("delete from texts where repo = ?", (name,))
	conn.execute("delete from owners where repo = ?", (name,))
	conn.execute("delete from files where repo = ?", (name,))
	for path in state:
		with open(path) as f:
			data = f.read()
		conn.execute("""insert into files(name, repo, path, mtime, data)
			values(?, ?, ?, ?, ?)""", (
			os.path.splitext(os.path.basename(path))[0],
			name,
			os.path.relpath(path, repo_dir),
			int(os.stat(path).st_mtime),
			data
		))
		print(os.path.splitext(os.path.basename(path))[0], name)
	xml_paths = {os.path.basename(os.path.splitext(xml_name)[0]): xml_name for xml_name in state}
	paths = texts.gather_web_pages(xml_paths)
	repo_dir = os.path.join(config.REPOS_DIR, name)
	for xml_name, html_path in sorted(paths.items()):
		xml_path = os.path.relpath(xml_paths[xml_name], repo_dir)
		if html_path:
			html_path = os.path.relpath(html_path, repo_dir)
		else:
			assert html_path is None
		file_id = os.path.basename(os.path.splitext(xml_path)[0])
		conn.execute("insert into texts(name, repo, html_path) values(?, ?, ?)",
			(file_id, name, html_path))
		for author_id in texts.owners_of(os.path.join(repo_dir, xml_path)):
			conn.execute("insert into owners(name, repo, git_name) values(?, ?, ?)",
				(file_id, name, author_id))
	for text, errors in sorted(state.items()):
		valid = not errors["schema"] and not errors["unicode"]
		errors = json.dumps(errors)
		file_id = os.path.basename(os.path.splitext(text)[0])
		conn.execute("""insert into validation(name, repo, code_hash, valid, errors, when_validated)
			values(?, ?, ?, ?, ?, strftime('%s', 'now'))""", (file_id, name, config.CODE_HASH, valid, errors))
	catalog.process_repo(name, conn)

def backup_to_jawakuno():
	command("bash -x %s" % os.path.join(config.THIS_DIR, "backup_to_jawakuno.sh"), capture_output=False, shell=True)

@TEXTS_DB.transaction
def handle_changes(name):
	conn = TEXTS_DB
	conn.execute("begin immediate")
	update_repo(name)
	update_db(conn, name)
	conn.execute("replace into metadata values('last_updated', strftime('%s', 'now'))")
	conn.execute("commit")
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
FORCE_UPDATE_DELTA = 24 * 60 * 60

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
			biblio.update()
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

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("-k", "--skip-update", action="store_true")
	args = parser.parse_args()
	if args.skip_update:
		NEXT_FULL_UPDATE += FORCE_UPDATE_DELTA
	main()
