import os, sys, subprocess, json, select, errno, logging
from dharma import config, validate, texts, biblio, grapheme
from dharma.config import command

FIFO_ADDR = os.path.join(config.REPOS_DIR, "change.hid")

REPOS = """
aditia-phd
arie
arie-corpus
BESTOW
digital-areal
electronic-texts
erc-dharma.github.io
exchange_aurorachana
lexica-indices
mdt-artefacts
mdt-authorities
mdt-editor
mdt-surrogates
mdt-texts
project-documentation
repo-test
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

SCHEMA = """
create table if not exists metadata(
	key text primary key,
	value blob
);
insert or ignore into metadata values('last_updated', 0);

create table if not exists commits(
	repo text,
	commit_hash text,
	commit_date integer,
	primary key(repo, commit_hash)
);

create view if not exists latest_commits(
	repo,
	commit_hash,
	commit_date
) as select repo, commit_hash, commit_date
	from commits group by repo having max(commit_date)
	order by commit_date desc;

create table if not exists texts(
	name text,
	repo text,
	commit_hash text,
	xml_path text,
	html_path text,
	primary key(name, repo, commit_hash),
	foreign key(repo, commit_hash) references commits(repo, commit_hash)
);

create table if not exists validation(
	name text,
	repo text,
	commit_hash text,
	code_hash text,
	valid boolean,
	errors json,
	when_validated integer,
	primary key(name, repo, commit_hash),
	foreign key(name, repo, commit_hash) references texts(name, repo, commit_hash)
);

create table if not exists owners(
	author_id text,
	repo text,
	xml_path text,
	primary key(author_id, repo, xml_path)
);
"""

TEXTS_DB = config.open_db("texts")
TEXTS_DB.executescript(SCHEMA)
TEXTS_DB.commit()

def update_repo(name):
	return command("git", "-C", os.path.join(config.REPOS_DIR, name), "pull", capture_output=False)

def latest_commit_in_repo(name):
	r = command("git", "-C", os.path.join(config.REPOS_DIR, name), "log", "-1", "--format=%H %at")
	hash, date = r.stdout.strip().split()
	date = int(date)
	return hash, date

def update_db(conn, name):
	commit_hash, date = latest_commit_in_repo(name)
	have_commit = False
	if conn.execute("select 1 from commits where repo = ? and commit_hash = ?",
		(name, commit_hash)).fetchone():
		have_commit = True
		if conn.execute("select 1 from validation where repo = ? and commit_hash = ? and code_hash = ?",
			(name, commit_hash, config.CODE_HASH)).fetchone():
			# No need to revalidate
			return
	if not have_commit:
		conn.execute("insert into commits(repo, commit_hash, commit_date) values(?, ?, ?)",
			(name, commit_hash, date))
	schema_errs = validate.validate_repo(name)
	unicode_errs = grapheme.validate_repo(name)
	state = {}
	for file in schema_errs:
		state[file] = {
			"schema": schema_errs[file],
			"unicode": unicode_errs[file],
		}
	if not have_commit:
		xml_paths = {os.path.basename(os.path.splitext(xml_name)[0]): xml_name for xml_name in state}
		paths = texts.gather_web_pages(xml_paths)
		repo_dir = os.path.join(config.REPOS_DIR, name)
		conn.execute("delete from owners where repo = ?", (name,))
		for xml_name, html_path in sorted(paths.items()):
			xml_path = os.path.relpath(xml_paths[xml_name], repo_dir)
			if html_path:
				html_path = os.path.relpath(html_path, repo_dir)
			else:
				assert html_path is None
			file_id = os.path.basename(os.path.splitext(xml_path)[0])
			conn.execute("insert into texts(name, repo, commit_hash, xml_path, html_path) values(?, ?, ?, ?, ?)",
				(file_id, name, commit_hash, xml_path, html_path))
			for author_id in texts.owners_of(os.path.join(repo_dir, xml_path)):
				conn.execute("insert into owners(author_id, repo, xml_path) values(?, ?, ?)",
					(author_id, name, xml_path))
	for text, errors in sorted(state.items()):
		valid = not errors["schema"] and not errors["unicode"]
		errors = json.dumps(errors)
		file_id = os.path.basename(os.path.splitext(text)[0])
		conn.execute("""insert or replace into validation(name, repo, commit_hash, code_hash, valid, errors, when_validated)
			values(?, ?, ?, ?, ?, ?, strftime('%s', 'now'))""", (file_id, name, commit_hash, config.CODE_HASH, valid, errors))

def handle_changes(name):
	conn = TEXTS_DB
	conn.execute("begin")
	try:
		update_db(conn, name)
		conn.execute("replace into metadata values('last_updated', strftime('%s', 'now'))")
		conn.execute("commit")
	except Exception as e:
		conn.execute("rollback")
		raise

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

def read_changes(fd):
	buf = ""
	while True:
		while True:
			end = buf.find("\n")
			if end >= 0:
				break
			data = os.read(fd, 512)
			while not data:
				logging.info("selecting")
				select.select([fd], [], [], 6000)
				data = os.read(fd, 512)
				logging.info("read %d" % len(data))
			buf += data.decode("ascii")
		name = buf[:end].rstrip("/")
		buf = buf[end + 1:]
		if name == "all":
			logging.info("updating everything...")
			for name in REPOS:
				update_repo(name)
				handle_changes(name)
			biblio.update()
			logging.info("updated everything")
		elif name == "bib":
			logging.info("updating biblio...")
			biblio.update()
			logging.info("updated biblio")
		elif name in REPOS:
			logging.info("updating single repo %r..." % name)
			update_repo(name)
			handle_changes(name)
			logging.info("updated single repo %r" % name)
		else:
			logging.warning("junk command: %r" % name)

def main():
	try:
		os.mkdir(config.REPOS_DIR)
	except FileExistsError:
		pass
	clone_all()
	try:
		os.mkfifo(FIFO_ADDR)
	except FileExistsError:
		pass
	logging.info("ready")
	fd = os.open(FIFO_ADDR, os.O_RDWR)
	try:
		read_changes(fd)
	finally:
		os.close(fd)

# To be used by the client
def notify(name):
	fd = os.open(FIFO_ADDR, os.O_RDWR | os.O_NONBLOCK)
	try:
		os.write(fd, name.encode("ascii") + b"\n")
	finally:
		os.close(fd)

if __name__ == "__main__":
	while True:
		try:
			main()
		except KeyboardInterrupt:
			break
		except Exception as e:
			print(e, file=sys.stderr)
