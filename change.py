import os, sys, subprocess, sqlite3, json, select
from dharma import config, validate, texts

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

TEXT_DB_PATH = os.path.join(config.DBS_DIR, "texts.sqlite")

SCHEMA = """
pragma foreign_keys = on;
pragma journal_mode = wal;
pragma page_size = 8192;

create table if not exists commits(
	repo text,
	commit_hash text,
	commit_date integer,
	primary key(repo, commit_hash)
);

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
	primary key(name, repo, commit_hash),
	foreign key(name, repo, commit_hash) references texts(name, repo, commit_hash)
);
"""

TEXT_DB = sqlite3.connect(TEXT_DB_PATH)
TEXT_DB.executescript(SCHEMA)

def command(*cmd):
	print(*cmd, file=sys.stderr)
	return subprocess.run(cmd, encoding="UTF-8", capture_output=True, check=True)

def update_repo(name):
	command("git", "-C", os.path.join(config.REPOS_DIR, name), "pull")

def latest_commit_in_repo(name):
	r = command("git", "-C", os.path.join(config.REPOS_DIR, name), "log", "-1", "--format=%T %at")
	hash, date = r.stdout.strip().split()
	date = int(date)
	return hash, date

def handle_changes(name):
	conn = TEXT_DB
	conn.execute("begin immediate")
	commit_hash, date = latest_commit_in_repo(name)
	if conn.execute("select 1 from commits where repo = ? and commit_hash = ?", (name, commit_hash)).fetchone():
		conn.execute("rollback")
		return
	conn.execute("insert into commits(repo, commit_hash, commit_date) values(?, ?, ?)",
		(name, commit_hash, date))
	state = validate.validate_repo(name)
	paths = texts.gather_web_pages(state)
	for xml_path, html_path in sorted(paths.items()):
		xml_path = os.path.relpath(xml_path, config.REPOS_DIR)
		if html_path:
			html_path = os.path.relpath(html_path, config.REPOS_DIR)
		else:
			assert html_path is None
		file_id = os.path.basename(os.path.splitext(xml_path)[0])
		conn.execute("insert into texts(name, repo, commit_hash, xml_path, html_path) values(?, ?, ?, ?, ?)",
			(file_id, name, commit_hash, xml_path, html_path))
	code_hash = command("git", "rev-parse", "HEAD").stdout.strip()
	for text, errors in sorted(state.items()):
		valid = not errors
		errors = json.dumps(errors)
		file_id = os.path.basename(os.path.splitext(text)[0])
		conn.execute("""insert into validation(name, repo, commit_hash, code_hash, valid, errors)
			values(?, ?, ?, ?, ?, ?)""", (file_id, name, commit_hash, code_hash, valid, errors))
	conn.execute("commit")

def clone_all():
	for name in REPOS:
		command("git", "clone", f"git@github.com:erc-dharma/{name}.git", os.path.join(config.REPOS_DIR, name))

def read_changes(fd):
	buf = ""
	while True:
		while True:
			end = buf.find("\n")
			if end >= 0:
				break
			data = os.read(fd, 512)
			while not data:
				select.select([fd], [], [], 0)
				data = os.read(fd, 512)
			buf += data.decode("ascii")
		name = buf[:end].rstrip("/")
		buf = buf[end + 1:]
		if name == "all":
			names = REPOS
		elif not name in REPOS:
			print("junk repo name: %r" % name, file=sys.stderr)
			continue
		else:
			names = [name]
		for name in names:
			update_repo(name)
			handle_changes(name)

def main():
	try:
		os.mkdir(config.REPOS_DIR)
		clone_all()
	except FileExistsError:
		pass
	try:
		os.mkfifo(FIFO_ADDR)
	except FileExistsError:
		pass
	fd = os.open(FIFO_ADDR, os.O_RDONLY)
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
	main()
