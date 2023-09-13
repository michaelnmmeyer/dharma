import os, unicodedata
from dharma import tree, transform, texts, config

# TODO useful fields to incl in catalog:
# https://erc-dharma.github.io/tfa-pallava-epigraphy/texts/htmloutput/DHARMA_INSPallava00280.html
# also lang (but for now language codes are a mess).

CATALOG_DB = config.open_db("catalog")
CATALOG_DB.executescript("""
create table if not exists metadata(
	key text primary key,
	value blob
);
create table if not exists documents(
	name text primary key,
	repo text,
	title json,
	author text,
	editors json,
	summary text
);
create virtual table if not exists documents_index using fts5(
	name unindexed, -- text primary key
	ident,
	repo,
	title,
	author,
	editor,
	summary,
	-- foreign key(name) references documents(name),
	tokenize="trigram"
);
""")
CATALOG_DB.commit()
CATALOG_DB.execute("attach database ? as texts", (config.db_path("texts"),))

def process_file(repo_name, path):
	t = tree.parse(path)
	p = transform.Parser(t)
	p.dispatch(p.tree.root)
	doc = p.document
	doc.repository = repo_name
	return doc

def normalize(s):
	if s is None:
		s = ""
	elif not isinstance(s, str):
		# make sure matching doesn't work across array elements
		s = "!!!!!".join(s)
	s = unicodedata.normalize("NFKD", s)
	s = "".join(c for c in s if not unicodedata.combining(c))
	s = s.casefold()
	s = s.replace("œ", "oe").replace("æ", "ae").replace("ß", "ss").replace("đ", "d")
	return unicodedata.normalize("NFC", s.strip())

# found a while ago some python code that implements the unicode collation algorithm.
# use it? or ICU? worth it?
def collate_title(s):
	ret = "".join(c for c in normalize(s) if c.isalnum())
	return ret or "zzzzzz" # yeah I know

CATALOG_DB.create_function("collate_title", 1, collate_title, deterministic=True)

def process_repo(name, db):
	for text in texts.iter_texts_in_repo(name):
		doc = process_file(name, text)
		db.execute("""insert into documents(name, repo, title, author, editors, summary)
			values (?, ?, ?, ?, ?, ?)""", (doc.ident, doc.repository, doc.title, doc.author, doc.editors, doc.summary))
		db.execute("""insert into documents_index(name, ident, repo, title, author, editor, summary)
			values (?, ?, ?, ?, ?, ?, ?)""", (doc.ident, normalize(doc.ident),
			normalize(doc.repository), normalize(doc.title), normalize(doc.author),
			normalize(doc.editors), normalize(doc.summary)))

def search(q):
	sql = """
		select documents.name, documents.repo, documents.title,
			documents.author, documents.editors, documents.summary,
			printf('https://erc-dharma.github.io/%s/%s', documents.repo, html_path) as html_link
		from documents join documents_index on documents.name = documents_index.name
		natural join texts.texts natural join texts.latest_commits
	"""
	q = " ".join(normalize(t) for t in q.split() if t not in ("AND", "OR", "NOT"))
	if q:
		q = (q,)
		sql += "where documents_index match ?"
	else:
		q = ()
	sql += " order by collate_title(documents.title)"
	db = CATALOG_DB.cursor()
	db.execute("begin")
	ret = db.execute(sql, q).fetchall()
	(last_modified,) = db.execute("select value from meta where key = 'last_modified'").fetchone()
	db.execute("commit")
	return ret, last_modified

def make_db():
	db = CATALOG_DB.cursor()
	db.execute("begin")
	db.execute("delete from documents")
	db.execute("delete from documents_index")
	for repo in os.listdir(config.REPOS_DIR):
		full_path = os.path.join(config.REPOS_DIR, repo)
		if not os.path.isdir(full_path):
			continue
		print(repo)
		process_repo(repo, db)
	db.execute("insert or replace into metadata values('last_modified', strftime('%s', 'now'))")
	db.execute("commit")
	db.execute("vacuum")
	db.close()

if __name__ == "__main__":
	make_db()
