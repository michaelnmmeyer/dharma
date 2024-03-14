import os, json, sys, unicodedata, hashlib, locale, time
from datetime import datetime
import flask
from dharma import config, change, people, ngrams, catalog, parse, validate, parse_ins, biblio, document, tree

app = flask.Flask(__name__, static_url_path="")
app.jinja_options["line_statement_prefix"] = "%"

@app.get("/")
def index():
	date = config.format_date(config.CODE_DATE)
	return flask.render_template("index.tpl", code_hash=config.CODE_HASH, code_date=date)

def is_robot(email):
	return email in ("readme-bot@example.com", "github-actions@github.com")

@app.get("/documentation")
def show_documentation():
	return flask.render_template("documentation.tpl")

@app.get("/documentation/<name>")
def show_tei_doc(name):
	path = config.path_of("schemas", name + ".html")
	with open(path) as f:
		return f.read()

@app.get("/texts")
@config.transaction("texts")
def show_texts():
	conn = config.open_db("texts")
	conn.execute("begin")
	(last_updated,) = conn.execute("select format_date(value) from metadata where key = 'last_updated'").fetchone()
	owner = flask.request.args.get("owner")
	severity = flask.request.args.get("severity")
	if severity not in ("warning", "error", "fatal"):
		severity = "warning"
	if severity == "warning":
		min_status = validate.WARNING
	elif severity == "error":
		min_status = validate.ERROR
	else:
		assert severity == "fatal"
		min_status = validate.FATAL
	if owner:
		rows = conn.execute("""
			select texts.name, commits.repo, commit_hash,
				format_date(commit_date) as readable_commit_date, status
			from texts
				join owners on texts.name = owners.name
				join commits on texts.repo = commits.repo
				join people_github on owners.git_name = people_github.git_name
			where dh_id = ? and status >= ?
			order by texts.name""", (owner, min_status)).fetchall()
	else:
		rows = conn.execute("""
			select texts.name, commits.repo, commit_hash,
				format_date(commit_date) as readable_commit_date, status
			from texts join commits on texts.repo = commits.repo
			where status >= ?
			order by name""", (min_status,)).fetchall()
	authors = conn.execute("""
		select distinct dh_id, print_name
		from people_main natural join people_github
			join owners on people_github.git_name = owners.git_name
		order by print_name""").fetchall()
	conn.execute("rollback")
	return flask.render_template("texts.tpl", last_updated=last_updated, texts=rows, authors=authors, owner=owner, severity=severity)

# XXX simplify URL
@app.get("/texts/<name>")
@config.transaction("texts")
def show_text(name):
	db = config.open_db("texts")
	row = db.execute("""
		select name, commits.repo, commit_hash, code_hash, status, path as xml_path, html_path,
			format_date(commit_date) as readable_commit_date
		from texts natural join files
			join commits on texts.repo = commits.repo
		where name = ?
	""", (name,)).fetchone()
	if not row:
		return flask.abort(404)
	url = config.format_url("https://github.com/erc-dharma/%s/blob/%s/%s",
		row['repo'], row['commit_hash'], row['xml_path'])
	if row["status"] == validate.OK:
		return flask.redirect(url)
	path = os.path.join(config.REPOS_DIR, row["repo"], row["xml_path"])
	return flask.render_template("invalid-text.tpl", text=row, github_url=url, result=validate.file(path))

# Legacy url
@app.get("/texts/<repo>/<hash>/<name>")
def show_text_legacy(repo, hash, name):
	return flask.redirect(config.format_url("/texts/%s", name))

@app.get("/repositories")
@config.transaction("texts")
def show_repos():
	db = config.open_db("texts")
	rows = db.execute("""
	with repos_editors as (
		select repo as name,
			json_each.value as editor,
			count(*) as editor_prod
		from documents, json_each(documents.editors)
		group by repo, json_each.value
		order by repo asc, editor_prod desc
	), repos_prod as (
		select repos.repo as name,
			repos.title as title,
			count(*) as repo_prod
		from repos join documents on repos.repo = documents.repo
		group by documents.repo
	) select repos_editors.name as name,
		repo_prod,
		title,
		json_group_array(json_array(editor, editor_prod)) as people
	from repos_editors join repos_prod on repos_editors.name = repos_prod.name
	group by repos_prod.name order by repos_prod.title""").fetchall()
	return flask.render_template("repos.tpl", rows=rows, json=json)

@app.get("/parallels")
@config.transaction("ngrams")
def show_parallels():
	db = config.open_db("ngrams")
	db.execute("begin")
	(date,) = db.execute("""select format_date(value)
		from metadata where key = 'last_updated'""").fetchone()
	rows = db.execute("select * from sources where verses + hemistiches + padas > 0")
	db.execute("commit")
	return flask.render_template("parallels.tpl", data=rows, last_updated=date)

parallels_types = {
	"verses": 1,
	"hemistiches": 2,
	"padas": 4,
}

@app.get("/parallels/texts/<text>/<category>")
@config.transaction("ngrams")
def show_parallels_details(text, category):
	db = config.open_db("ngrams")
	type = parallels_types[category]
	rows = db.execute("""
		select id, number, contents, parallels from passages
		where type = ? and file = ? and parallels > 0
	""", (type, text))
	return flask.render_template("parallels_details.tpl", file=text, category=category, data=rows)

@app.get("/parallels/texts/<text>/<category>/<int:id>")
@config.transaction("ngrams")
def show_parallels_full(text, category, id):
	db = config.open_db("ngrams")
	type = parallels_types[category]
	db.execute("begin")
	ret = db.execute("""
		select number, contents from passages where type = ? and id = ?
		""", (type, id)).fetchone()
	if not ret:
		return flask.abort(404)
	number, contents = ret
	rows = db.execute("""
		select file, number, contents, id2, coeff
		from passages join jaccard on passages.id = jaccard.id2
		where jaccard.type = ? and jaccard.id = ?
		order by coeff desc
	""", (type, id)).fetchall()
	db.execute("commit")
	return flask.render_template("parallels_enum.tpl", category=category, file=text,
		number=number, data=rows, contents=contents)

@app.get("/catalog")
def show_catalog():
	q = flask.request.args.get("q", "")
	s = flask.request.args.get("s", "")
	rows, last_updated = catalog.search(q, s)
	return flask.render_template("catalog.tpl", rows=rows, q=q, s=s, last_updated=last_updated, json=json)

@app.get("/langs")
@config.transaction("texts")
def show_langs():
	db = config.open_db("texts")
	rows = db.execute("""
	select langs_list.inverted_name as name,
		json_group_array(distinct(langs_by_code.code)) as codes,
		printf('639-%d', iso) as iso
	from documents
		join json_each(documents.langs)
		join langs_list on langs_list.id = json_each.value
		join langs_by_code on langs_list.id = langs_by_code.id
	group by langs_list.id order by langs_list.inverted_name collate icu""").fetchall()
	return flask.render_template("langs.tpl", rows=rows, json=json)

@app.get("/parallels/search")
def search_parallels():
	text = flask.request.args.get("text")
	orig_text = text
	type = flask.request.args.get("type")
	if not text or not type:
		return flask.redirect("/parallels")
	text = unicodedata.normalize("NFC", text)
	page = flask.request.args.get("page")
	if page and page.isdigit():
		page = int(page)
		if page < 1:
			page = 1
	else:
		page = 1
	ret, formatted_text, page, per_page, total = ngrams.search(text, type, page)
	return flask.render_template("parallels_search.tpl",
		data=ret, text=formatted_text,
		category=type,
		category_plural=type + (type == "hemistich" and "es" or "s"),
		page=page,
		per_page=per_page,
		orig_text=orig_text,
		total=total)

@app.get("/display")
@config.transaction("texts")
def display_home():
	db = config.open_db("texts")
	texts = [t for (t,) in db.execute("select name from texts where name glob 'DHARMA_INS*'")]
	return flask.render_template("display.tpl", texts=texts)

@app.get("/display/<text>")
@config.transaction("texts")
def display_text(text):
	db = config.open_db("texts")
	row = db.execute("""
		select
			printf('%s/%s/%s', ?, repo, path) as path,
			repo,
			commit_hash,
			format_date(commit_date) as commit_date,
			format_date(last_modified) as last_modified,
			last_modified_commit,
			format_url('https://github.com/erc-dharma/%s/blob/%s/%s', repo, commit_hash, path) as github_url
		from texts natural join files natural join commits
		where name = ?""",
		(config.REPOS_DIR, text)).fetchone()
	if not row:
		return flask.abort(404)
	import parse_ins
	try:
		doc = parse_ins.process_file(row["path"], db)
		title = doc.title.render_logical()
		doc.title = title and title.split(document.PARA_SEP) or []
		editors = doc.editors.render_logical()
		doc.editors = editors and editors.split(document.PARA_SEP)
	except tree.Error as e:
		doc = document.Document()
		doc.valid = False
		doc.ident = text
	doc.repository = row["repo"]
	doc.commit_hash, doc.commit_date = row["commit_hash"], row["commit_date"]
	doc.last_modified = row["last_modified"]
	doc.last_modified_commit = row["last_modified_commit"]
	return flask.render_template("inscription.tpl", doc=doc,
		github_url=row["github_url"], text=text, numberize=parse.numberize)

@app.post("/convert")
def convert_text():
	file = flask.request.files.get("file")
	name = os.path.splitext(os.path.basename(file.filename))[0]
	import parse_ins
	doc = parse_ins.process_file(file.file, path=name)
	title = doc.title.render_logical()
	doc.title = title and title.split(document.PARA_SEP) or []
	editors = doc.editors.render_logical()
	doc.editors = editors and editors.split(document.PARA_SEP)
	return flask.render_template("inscription.tpl", doc=doc, text=name,
		numberize=parse.numberize, root="https://dharman.in")
	# XXX root does not work for bib entries, make it global

@app.get("/test")
def test():
	return flask.render_template("test.tpl")

@app.get("/bibliography/page/<int:page>")
@config.transaction("texts")
def display_biblio_page(page):
	db = config.open_db("texts")
	db.execute("begin")
	(entries_nr,) = db.execute("select count(*) from biblio_data where sort_key is not null").fetchone()
	pages_nr = (entries_nr + biblio.PER_PAGE - 1) // biblio.PER_PAGE
	if page < 1:
		page = 1
	elif page > pages_nr:
		page = pages_nr
	entries = []
	for key, entry in db.execute("""select key, json ->> '$.data' from biblio_data
		where sort_key is not null
		order by sort_key limit ? offset ?""", (biblio.PER_PAGE, (page - 1) * biblio.PER_PAGE)):
		entries.append(biblio.format_entry(key, json.loads(entry), loc=[], n=None))
	db.execute("commit")
	first_entry = (page - 1) * biblio.PER_PAGE + 1
	if first_entry < 0:
		first_entry = 0
	last_entry = page * biblio.PER_PAGE
	if last_entry > entries_nr:
		last_entry = entries_nr
	return flask.render_template("biblio.tpl", page=page, pages_nr=pages_nr,
		entries=entries, entries_nr=entries_nr, per_page=biblio.PER_PAGE,
		first_entry=first_entry, last_entry=last_entry)

@app.get("/bibliography")
def display_biblio():
	return flask.redirect("/bibliography/page/1")

@app.post("/validate/oxygen")
def do_validate():
	upload = flask.request.files.get("upload")
	if validate.schema_from_filename(upload.filename) != "inscription":
		yield "Type: F\n"
		yield "Description: cannot validate this file (not an inscription)\n"
		yield "\n"
		return
	doc = parse_ins.process_file(upload.file)
	errs = sorted(doc.tree.bad_nodes, key=lambda node: node.location)
	if not errs:
		yield "Type: W\n"
		yield "SystemID: %s\n" % upload.filename
		yield "Description: OK\n"
		yield "\n"
		return
	for node in errs:
		line, col = node.location
		yield "Type: E\n"
		yield "SystemID: %s\n" % upload.filename
		yield "Line: %d\n" % 20
		yield "Column: %d\n" % 10
		yield "EndLine: %d\n" % 20
		yield "EndColumn: %d\n" % 15
		yield "Description: %s\n" % ", ".join(node.problems)
		yield "\n"
		break

@app.post("/github-event")
def handle_github():
	js = flask.request.json
	repo = js["repository"]["name"]
	if not js.get("commits"):
		return
	# XXX remove special case, add hooks or something for each repo
	if repo != "tfd-nusantara-philology" and all(is_robot(commit["author"]["email"]) for commit in js["commits"]):
		return
	change.notify(repo)

if __name__ == "__main__":
	app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
	# To run with gunicorn, use:
	# gunicorn -w 4 -b localhost:8023 dharma.server:app
