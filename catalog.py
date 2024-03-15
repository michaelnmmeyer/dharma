import os, sys
from dharma import tree, parse, texts, config, document

class Query:

	def __init__(self, query, field=""):
		self.query = query
		self.field = field

	def __str__(self):
		if isinstance(self.query, str):
			ret = '"%s"' % self.query.replace('"', '""')
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

def delete(name, db):
	db.execute("delete from documents_index where name = ?", (name,))
	db.execute("delete from documents where name = ?", (name,))

def process_file(repo, path):
	print(path)
	db = config.open_db("texts")
	try:
		t = tree.parse(path)
	except tree.Error as e:
		print("catalog: %r %s" % (path, e), file=sys.stderr)
		doc = document.Document()
		doc.repository = repo
		doc.ident = os.path.splitext(os.path.basename(path))[0]
		doc.langs = ["und"]
		return doc
	langs = set()
	for node in t.find("//*"):
		if not "lang" in node.attrs:
			continue
		lang = node["lang"]
		(code,) = db.execute("select ifnull((select id from langs_by_code where code = ?), 'und')", (lang,)).fetchone()
		langs.add(code)
	if not langs:
		langs.add("und")
	# Delete <body> so that we don't process the whole file.
	node = t.first("//body")
	if node is not None:
		node.delete()
	p = parse.Parser(t, parse.make_handlers_map())
	p.dispatch(p.tree.root)
	doc = p.document
	doc.langs = sorted(langs)
	doc.repository = repo
	return doc

def insert(file, db):
	doc = process_file(file.repo, file.full_path)
	if not doc:
		return
	for key in ("title", "author", "editors", "summary"):
		val = getattr(doc, key)
		if val is None:
			val = parse.Block(val)
			val.finish()
			setattr(doc, key, val)
	fmt_title = doc.title.render_logical()
	if fmt_title:
		fmt_title = fmt_title.split(document.PARA_SEP)
	else:
		fmt_title = []
	fmt_editors = doc.editors.render_logical()
	if fmt_editors:
		fmt_editors = fmt_editors.split(document.PARA_SEP)
	else:
		fmt_editors = []
	db.execute("""insert or replace into documents(name, repo, title, author, editors, langs, summary)
		values (?, ?, ?, ?, ?, ?, ?)""", (doc.ident, doc.repository,
			fmt_title, doc.author.render_logical(), fmt_editors,
			doc.langs, doc.summary.render_logical()))
	# No primary key on documents_index, so we cannot use "insert or replace"
	db.execute("delete from documents_index where name = ?", (doc.ident,))
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

def patch_languages(db, q):
	for clause in q.clauses:
		if clause.field != "lang":
			continue
		text = clause.query
		assert isinstance(text, str)
		if len(text) <= 3:
			(text,) = db.execute("select ifnull((select id from langs_by_code where code = ?), '')", (text,)).fetchone()
			clause.query = text
			continue
		langs = [Query(lang) for (lang,) in db.execute("select id from langs_by_name where name match ?", (text,))]
		if langs:
			clause.query = OR(langs)
		else:
			clause.query = "" # prevent matching

@config.transaction("texts")
def search(q, s):
	db = config.open_db("texts")
	db.execute("begin")
	sql = """
		select documents.name, documents.repo, documents.title,
			documents.author, documents.editors, json_group_array(distinct langs_list.name) as langs, documents.summary,
			format_url('https://erc-dharma.github.io/%s/%s', documents.repo, html_path) as html_link
		from documents
			join documents_index on documents.name = documents_index.name
			natural join texts
			join json_each(documents.langs)
			join langs_by_code on langs_by_code.code = json_each.value
			join langs_list on langs_list.id = langs_by_code.id
	"""
	q = " ".join(document.normalize(t) for t in q.split() if t not in ("AND", "OR", "NOT"))
	if q:
		q = parse_query(q)
		patch_languages(db, q)
		q = (str(q),)
		sql += " where documents_index match ? "
	else:
		q = ()
	if s == "ident":
		s = "name"
	elif s == "title" or s == "repo":
		pass
	else:
		s = "title"
	sql += " group by documents.name order by documents.%s collate icu " % s
	ret = db.execute(sql, q).fetchall()
	(last_updated,) = db.execute("""
		select format_date(value)
		from metadata where key = 'last_updated'""").fetchone()
	db.execute("commit")
	return ret, last_updated
