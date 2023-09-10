import os
from dharma import tree, transform, texts, config

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

def process_repo(name):
	for text in texts.iter_texts_in_repo(name):
		doc = process_file(name, text)
		CATALOG_DB.execute("""insert into documents(name, repo, title, editors)
			values (?, ?, ?, ?)""", (doc.ident, doc.repository, doc.title, doc.editors))

def make_db():
	for repo in os.listdir(config.REPOS_DIR):
		full_path = os.path.join(config.REPOS_DIR, repo)
		if not os.path.isdir(full_path):
			continue
		print(repo)
		process_repo(repo)
	CATALOG_DB.commit()

if __name__ == "__main__":
	make_db()
