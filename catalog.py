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
	langs json,
	summary text
);
create virtual table if not exists documents_index using fts5(
	name unindexed, -- text primary key references documents(name)
	ident,
	repo,
	title,
	author,
	editor,
	lang,
	summary,
	tokenize="trigram"
);
""")
CATALOG_DB.commit()
CATALOG_DB.execute("attach database ? as texts", (config.db_path("texts"),))

LANGS_DB = config.open_db("langs")
LANGS_DB.execute("attach database ? as catalog", (config.db_path("catalog"),))

class Query:

	def __init__(self, query, field=""):
		self.query = query
		self.field = field

	def __str__(self):
		if isinstance(self.query, str):
			ret = "%s" % self.query.replace('"', '""')
		else:
			ret = str(self.query)
		if self.field:
			ret = "%s:%s" % (self.field, ret)
		return ret

class AND(Query):

	def __init__(self, clauses):
		self.clauses = clauses

	def __str__(self):
		return "(%s)" % " AND ".join(str(clause) for clause in self.clauses)

class OR(Query):

	def __init__(self, clauses):
		self.clauses = clauses

	def __str__(self):
		return "(%s)" % " OR ".join(str(clause) for clause in self.clauses)


def process_file(repo_name, path):
	t = tree.parse(path)
	p = transform.Parser(t, transform.make_handlers_map())
	p.dispatch(p.tree.root)
	doc = p.document
	for node in t.find("//*"):
		if not "lang" in node.attrs:
			continue
		lang = node["lang"]
		# to fix, we don't have "Old Javanese" in ISO, should submit it
		if lang == "oj":
			lang = "jav"
		(code,) = LANGS_DB.execute("select ifnull((select id from by_code where code = ?), 'und')", (lang,)).fetchone()
		doc.langs.append(code)
	doc.langs = sorted(set(doc.langs))
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
		fmt_title = doc.title.render()
		if fmt_title:
			fmt_title = fmt_title.split(transform.PARA_SEP)
		else:
			fmt_title = []
		fmt_editors = doc.editors.render()
		if fmt_editors:
			fmt_editors = fmt_editors.split(transform.PARA_SEP)
		else:
			fmt_editors = []
		db.execute("""insert into documents(name, repo, title, author, editors, langs, summary)
			values (?, ?, ?, ?, ?, ?, ?)""", (doc.ident, doc.repository,
				fmt_title, doc.author.render(), fmt_editors,
				doc.langs, doc.summary.render()))
		db.execute("""insert into documents_index(name, ident, repo, title, author, editor, lang, summary)
			values (?, ?, ?, ?, ?, ?, ?, ?)""", (doc.ident, doc.ident.lower(),
			doc.repository.lower(), doc.title.searchable_text(), doc.author.searchable_text(),
			doc.editors.searchable_text(), "---".join(doc.langs), doc.summary.searchable_text()))

class InvalidQuery(Exception):
	pass

def tokenize_query(q):
	toks = []
	i = 0
	while i < len(q):
		c = q[i]
		if c == ":":
			toks.append(c)
			i += 1
		elif c == '"':
			i += 1
			tok = ""
			while i < len(q) and q[i] != '"':
				if q[i] == "\\":
					i += 1
					if i == len(q):
						raise InvalidQuery
				tok += q[i]
				i += 1
			if i == len(q):
				raise InvalidQuery
			toks.append(tok)
			i += 1
		elif c.isspace():
			i += 1
		else:
			i += 1
			tok = c
			while i < len(q) and q[i] not in ": ":
				if q[i] == "\\":
					i += 1
					if i == len(q):
						raise InvalidQuery
				tok += q[i]
				i += 1
			toks.append(tok)
	return toks

search_fields = {"ident", "repo", "title", "author", "editor", "summary", "lang"}

def parse_query(q):
	toks = tokenize_query(q)
	i = 0
	clauses = []
	while i < len(toks):
		if toks[i] == ":":
			raise InvalidQuery
		elif i + 1 < len(toks) and toks[i + 1] == ":":
			field = toks[i]
			if i + 2 < len(toks) and toks[i + 2] != ":":
				clauses.append(Query(toks[i + 2], field))
			i += 3
		else:
			clauses.append(Query(toks[i]))
			i += 1
	return AND(clauses)

def patch_languages(q):
	for clause in q.clauses:
		if clause.field != "lang":
			continue
		text = clause.query
		assert isinstance(text, str)
		if len(text) <= 3:
			(text,) = LANGS_DB.execute("select ifnull((select id from by_code where code = ?), '')", (text,)).fetchone()
			clause.query = text
			continue
		langs = [Query(lang) for (lang,) in LANGS_DB.execute("select id from by_name where name match ?", (text,))]
		if langs:
			clause.query = OR(langs)
		else:
			clause.query = "" # prevent matching

def search(q, s):
	sql = """
		select documents.name, documents.repo, documents.title,
			documents.author, documents.editors, documents.langs, documents.summary,
			printf('https://erc-dharma.github.io/%s/%s', documents.repo, html_path) as html_link
		from documents join documents_index on documents.name = documents_index.name
		natural join texts.texts natural join texts.commits
	"""
	q = " ".join(transform.normalize(t) for t in q.split() if t not in ("AND", "OR", "NOT"))
	if q:
		q = parse_query(q)
		with LANGS_DB:
			patch_languages(q)
		q = (str(q),)
		sql += "where documents_index match ?"
	else:
		q = ()
	if s == "ident":
		s = "name"
	elif s == "title" or s == "repo":
		pass
	else:
		s = "title"
	sql += " order by collate_title(documents.%s)" % s
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
