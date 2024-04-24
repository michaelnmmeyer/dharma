import logging
from dharma import parse, texts, common, document

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

def delete(name):
	db = common.db("texts")
	db.execute("delete from documents_index where name = ?", (name,))
	db.execute("delete from documents where name = ?", (name,))

def insert(file):
	db = common.db("texts")
	doc = parse.process_file(file, mode="catalog")
	for key in ("title", "author", "editors", "summary"):
		val = getattr(doc, key, None)
		if val is None:
			val = parse.Block(val)
			val.finish()
			setattr(doc, key, val)
	fmt_editors = doc.editors and doc.editors.render_logical() or []
	if fmt_editors:
		fmt_editors = fmt_editors.split(document.PARA_SEP)
	else:
		fmt_editors = []
	db.execute("""insert or replace into documents(name, repo, title,
		author, editors, editors_ids, langs, summary, html_path, status)
		values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (doc.ident, doc.repository,
			doc.title.render_logical() or None, doc.author.render_logical() or None, fmt_editors,
			doc.editors_ids,
			[lang.id for lang in doc.edition_langs], doc.summary.render_logical() or None,
			file.html, file.status))
	# No primary key on documents_index, so we cannot use "insert or replace"
	db.execute("delete from documents_index where name = ?", (doc.ident,))
	db.execute("""insert into documents_index(
		name, ident, repo, title, author,
		editor, editor_id, lang, summary)
		values (?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
		doc.ident, doc.ident.lower(),
		doc.repository.lower(), doc.title.searchable_text(), doc.author.searchable_text(),
		doc.editors and doc.editors.searchable_text() or "",
		doc.editors_ids and "|||".join(doc.editors_ids) or "",
		"---".join(lang.id for lang in doc.edition_langs),
		doc.summary.searchable_text()))

# Rebuild the full catalog with the data already present in the db.
def rebuild():
	logging.info("rebuilding the catalog")
	db = common.db("texts")
	db.execute("delete from documents_index")
	for repo, path, mtime, data, html in db.execute("""
		select files.repo, path, mtime, data, html_path
		from files join documents on files.name = documents.name
		order by files.repo, files.name"""):
		file = texts.File(repo, path)
		file.html = html
		setattr(file, "_mtime", mtime)
		setattr(file, "_data", data)
		insert(file)
	logging.info("rebuilded the catalog")

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

search_fields = {
	"ident", "repo", "title", "author",
	"editor", "editor_id", "summary", "lang",
}

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
	db = common.db("texts")
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

def construct_query(q):
	q = " ".join(document.normalize(t) for t in q.split()
		if t not in ("AND", "OR", "NOT"))
	if q:
		q = parse_query(q)
		patch_languages(q)
		return str(q)

PER_PAGE = 50

@common.transaction("texts")
def search(q, sort, page):
	db = common.db("texts")
	q = construct_query(q)
	if q:
		(total,) = db.execute("""select count(*) from documents_index
			where documents_index match ?""", (q,)).fetchone()
	else:
		(total,) = db.execute("select count(*) from documents_index").fetchone()
	sql = """
		select documents.name, documents.repo, documents.title,
			documents.author, documents.editors, json_group_array(distinct langs_list.name) as langs, documents.summary,
			repos.title as repo_title,
			html_path
		from documents
			join documents_index on documents.name = documents_index.name
			join repos on documents.repo = repos.repo
			join json_each(documents.langs)
			left join langs_by_code on langs_by_code.code = json_each.value
			left join langs_list on langs_list.id = langs_by_code.id
	"""
	if q:
		sql += " where documents_index match ?"
	match sort:
		case "ident":
			sort = "name"
		case "title" | "repo":
			pass
		case _:
			sort = "title"
	sql += f"""
		group by documents.name order by documents.{sort} collate icu nulls last
		limit ? offset ?"""
	offset = (page - 1) * PER_PAGE
	limit = PER_PAGE
	if q:
		ret = db.execute(sql, (q, limit, offset)).fetchall()
	else:
		ret = db.execute(sql, (limit, offset)).fetchall()
	(last_updated,) = db.execute("""
		select cast(value as int)
		from metadata where key = 'last_updated'""").fetchone()
	return ret, total, PER_PAGE, last_updated
