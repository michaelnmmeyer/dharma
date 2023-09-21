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
insert or ignore into metadata values('last_updated', 0);
create table if not exists documents(
	name text primary key,
	repo text,
	title json,
	author text,
	editors json,
	summary text
);
create virtual table if not exists documents_index using fts5(
	name unindexed, -- text primary key references documents(name)
	ident,
	repo,
	title,
	author,
	editor,
	summary,
	tokenize="trigram"
);
""")
CATALOG_DB.commit()
CATALOG_DB.execute("attach database ? as texts", (config.db_path("texts"),))

def process_file(repo_name, path):
	t = tree.parse(path)
	p = transform.Parser(t, transform.make_handlers_map())
	p.dispatch(p.tree.root)
	doc = p.document
	doc.repository = repo_name
	return doc

# found a while ago some python code that implements the unicode collation algorithm.
# use it? or ICU? worth it?
def collate_title(s):
	s = " ".join(s)
	ret = "".join(c for c in transform.normalize(s) if c.isalnum())
	return ret or "zzzzzz" # yeah I know

CATALOG_DB.create_function("collate_title", 1, collate_title, deterministic=True)

def process_repo(name, db):
	for text in texts.iter_texts_in_repo(name):
		doc = process_file(name, text)
		for key in ("title", "author", "editors", "summary"):
			val = getattr(doc, key)
			if val is None:
				val = transform.Block(val)
				val.finish()
				setattr(doc, key, val)
		db.execute("""insert into documents(name, repo, title, author, editors, summary)
			values (?, ?, ?, ?, ?, ?)""", (doc.ident, doc.repository,
				doc.title.render().split(transform.PARA_SEP), doc.author.render(), doc.editors.render().split(transform.PARA_SEP),
				doc.summary.render()))
		db.execute("""insert into documents_index(name, ident, repo, title, author, editor, summary)
			values (?, ?, ?, ?, ?, ?, ?)""", (doc.ident, doc.ident.lower(),
			doc.repository.lower(), doc.title.searchable_text(), doc.author.searchable_text(),
			doc.editors.searchable_text(), doc.summary.searchable_text()))

def search(q):
	sql = """
		select documents.name, documents.repo, documents.title,
			documents.author, documents.editors, documents.summary,
			printf('https://erc-dharma.github.io/%s/%s', documents.repo, html_path) as html_link
		from documents join documents_index on documents.name = documents_index.name
		natural join texts.texts natural join texts.latest_commits
	"""
	q = " ".join(transform.normalize(t) for t in q.split() if t not in ("AND", "OR", "NOT"))
	if q:
		q = (q,)
		sql += "where documents_index match ?"
	else:
		q = ()
	sql += " order by collate_title(documents.title)"
	db = CATALOG_DB.cursor()
	db.execute("begin")
	ret = db.execute(sql, q).fetchall()
	(last_updated,) = db.execute("""
		select format_date(value)
		from metadata where key = 'last_updated'""").fetchone()
	db.execute("commit")
	return ret, last_updated

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
	db.execute("insert or replace into metadata values('last_updated', strftime('%s', 'now'))")
	db.execute("commit")
	db.execute("vacuum")
	db.close()

if __name__ == "__main__":
	make_db()
