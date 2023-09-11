import os, unicodedata
from dharma import tree, transform, texts, config

"""
make editors searchable first. how?

for filtering and facets must have a map

	editor_name(full) -> [doc ids]

"""

CATALOG_DB = config.open_db("catalog")
CATALOG_DB.executescript("""
create table if not exists documents(
	name text primary key,
	repo text,
	title json,
	author text,
	editors json
);
create virtual table if not exists documents_index using fts5(
	name unindexed,
	ident,
	repo,
	title,
	author,
	editor,
	tokenize="trigram"
);
""")
CATALOG_DB.execute("attach database ? as texts", (config.db_path("texts"),))
CATALOG_DB.commit()

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
		s = "!!!!!".join(s)
	# maybe see also https://github.com/JuliaStrings/utf8proc/blob/master/lump.md
	s = unicodedata.normalize("NFKD", s)
	s = "".join(c for c in s if not unicodedata.combining(c))
	s = s.casefold()
	s = s.replace("œ", "oe").replace("æ", "ae").replace("ß", "ss")
	return unicodedata.normalize("NFC", s.strip())

def process_repo(name, db):
	for text in texts.iter_texts_in_repo(name):
		doc = process_file(name, text)
		db.execute("""insert into documents(name, repo, title, author, editors)
			values (?, ?, ?, ?, ?)""", (doc.ident, doc.repository, doc.title, doc.author, doc.editors))
		db.execute("""insert into documents_index(name, ident, repo, title, author, editor)
			values (?, ?, ?, ?, ?, ?)""", (doc.ident, normalize(doc.ident),
			normalize(doc.repository), normalize(doc.title), normalize(doc.author),
			normalize(doc.editors)))

def search(q):
	sql = """
		select documents.name, documents.repo, documents.title, documents.author, documents.editors,
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
	sql += " order by documents.name"
	return CATALOG_DB.execute(sql, q).fetchall()

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
	db.execute("commit")
	db.close()

if __name__ == "__main__":
	make_db()
