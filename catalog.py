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
	editors json
);
""")
CATALOG_DB.commit()

def process_file(repo_name, path):
	t = tree.parse(path)
	p = transform.Parser(t)
	p.dispatch(p.tree.root)
	doc = p.document
	doc.repository = repo_name
	return doc

def normalize_name(name):
	# maybe see also https://github.com/JuliaStrings/utf8proc/blob/master/lump.md
	name = unicodedata.normalize("NFKD", name)
	name = "".join(c for c in name if not unicodedata.combining(c))
	name = name.casefold()
	name = name.replace("œ", "oe").replace("æ", "ae").replace("ß", "ss")
	return unicodedata.normalize("NFC", name.strip())

def match_name(names, q):
	if q == "*":
		return True
	return q in normalize_name(names)

def process_repo(name):
	for text in texts.iter_texts_in_repo(name):
		doc = process_file(name, text)
		CATALOG_DB.execute("""insert into documents(name, repo, title, editors)
			values (?, ?, ?, ?)""", (doc.ident, doc.repository, doc.title, doc.editors))

def make_db():
	db = CATALOG_DB.cursor()
	db.execute("begin")
	db.execute("delete from documents")
	for repo in os.listdir(config.REPOS_DIR):
		full_path = os.path.join(config.REPOS_DIR, repo)
		if not os.path.isdir(full_path):
			continue
		print(repo)
		process_repo(repo)
	db.execute("commit")
	db.close()

if __name__ == "__main__":
	make_db()
