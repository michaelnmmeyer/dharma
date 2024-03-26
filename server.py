import os, sys, unicodedata, hashlib, locale, time, datetime, html, urllib
import flask # pip install flask
from bs4 import BeautifulSoup # pip install bs4
from dharma import config, change, people, ngrams, catalog, parse, validate, parse_ins, biblio, document, tree, texts

app = flask.Flask(__name__, static_url_path="", template_folder="views")
app.jinja_options["line_statement_prefix"] = "%"

@app.template_filter("format_date")
def format_date(when):
	assert isinstance(when, int)
	when_obj = datetime.datetime.fromtimestamp(when).astimezone()
	when_detailed = html.escape(when_obj.strftime("%FT%T%z"))
	when_readable = html.escape(when_obj.strftime("%F %R"))
	return f'<time datetime="{when_detailed}">{when_readable}</time>'

@app.template_filter("quote_plus")
def quote_plus(s):
	return urllib.parse.quote_plus(s)

# Global variables accessible from within jinja templates.
templates_globals = {
	"code_date": config.CODE_DATE,
	"code_hash": config.CODE_HASH,
	"from_json": config.from_json,
	"format_url": config.format_url,
	"numberize": parse.numberize,
}
@app.context_processor
def inject_global_vars():
	return templates_globals

@app.get("/")
def index():
	return flask.render_template("index.tpl")

@app.get("/documentation")
def show_documentation():
	return flask.render_template("documentation.tpl")

@app.get("/documentation/<name>")
def show_tei_doc(name):
	path = config.path_of("schemas", name + ".html")
	with open(path) as f:
		return f.read()

@app.get("/errors")
@config.transaction("texts")
def show_texts_errors():
	conn = config.db("texts")
	conn.execute("begin")
	(last_updated,) = conn.execute("select cast(value as int) from metadata where key = 'last_updated'").fetchone()
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
			select documents.name, repos.repo, repos.commit_hash,
				repos.commit_date,
				documents.status
			from documents
				join repos on documents.repo = repos.repo
				join owners on documents.name = owners.name
				join people_github on owners.git_name = people_github.git_name
			where dh_id = ? and documents.status >= ?
			order by documents.name""", (owner, min_status)).fetchall()
	else:
		rows = conn.execute("""
			select documents.name, repos.repo, repos.commit_hash,
				repos.commit_date,
				documents.status
			from documents join repos on documents.repo = repos.repo
			where documents.status >= ?
			order by documents.name""", (min_status,)).fetchall()
	authors = conn.execute("""
		select distinct dh_id, print_name
		from people_main natural join people_github
			join owners on people_github.git_name = owners.git_name
		order by print_name""").fetchall()
	conn.execute("rollback")
	return flask.render_template("errors.tpl", last_updated=last_updated, texts=rows, authors=authors, owner=owner, severity=severity)

@app.get("/errors/<name>")
@config.transaction("texts")
def show_text_errors(name):
	db = config.db("texts")
	row = db.execute("""
		select documents.name, repos.repo, commit_hash, code_hash,
			status, mtime, path as xml_path, data, html_path,
			commit_date
		from documents join files on documents.name = files.name
			join repos on documents.repo = repos.repo
		where documents.name = ?
	""", (name,)).fetchone()
	if not row:
		return flask.abort(404)
	url = config.format_url("https://github.com/erc-dharma/%s/blob/%s/%s",
		row['repo'], row['commit_hash'], row['xml_path'])
	if row["status"] == validate.OK:
		return flask.redirect(url)
	path = config.path_of("repos", row["repo"], row["xml_path"])
	file = texts.File(row["repo"], row["xml_path"])
	file.html = row["html_path"]
	setattr(file, "_mtime", row["mtime"])
	setattr(file, "_data", row["data"])
	setattr(file, "_status", row["status"])
	return flask.render_template("invalid-text.tpl",
		text=row, github_url=url, result=validate.file(file))

@app.get("/repositories")
@config.transaction("texts")
def show_repos():
	db = config.db("texts")
	rows = db.execute("select * from repos_display").fetchall()
	return flask.render_template("repos.tpl", rows=rows)

@app.get("/parallels")
@config.transaction("ngrams")
def show_parallels():
	db = config.db("ngrams")
	db.execute("begin")
	(date,) = db.execute("""select cast(value as int)
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
	db = config.db("ngrams")
	type = parallels_types[category]
	rows = db.execute("""
		select id, number, contents, parallels from passages
		where type = ? and file = ? and parallels > 0
	""", (type, text))
	return flask.render_template("parallels_details.tpl", file=text, category=category, data=rows)

@app.get("/parallels/texts/<text>/<category>/<int:id>")
@config.transaction("ngrams")
def show_parallels_full(text, category, id):
	db = config.db("ngrams")
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
def legacy_show_catalog():
	return flask.redirect(flask.url_for("show_catalog"), code=302)

@app.get("/texts")
def show_catalog():
	q = flask.request.args.get("q", "")
	s = flask.request.args.get("s", "")
	rows, last_updated = catalog.search(q, s)
	return flask.render_template("texts.tpl",
		rows=rows, q=q, s=s, last_updated=last_updated)

@app.get("/editorial-conventions")
def show_editorial_conventions():
	return flask.render_template("editorial.tpl")

@app.get("/languages")
@config.transaction("texts")
def show_langs():
	db = config.db("texts")
	rows = db.execute("select * from langs_display").fetchall()
	return flask.render_template("langs.tpl", rows=rows)

@app.get("/langs")
def show_lang_old():
	return flask.redirect("/languages", code=301)

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
	db = config.db("texts")
	texts = [t for (t,) in db.execute("select name from documents where name glob 'DHARMA_INS*'")]
	return flask.render_template("display.tpl", texts=texts)

@app.get("/display/<text>")
def legacy_display_text(text):
	return flask.redirect(flask.url_for("display_text", text=text), code=302)

@app.get("/texts/<text>")
@config.transaction("texts")
def display_text(text):
	db = config.db("texts")
	db.execute("begin")
	row = db.execute("""
		select
			printf('%s/%s/%s', ?, repos.repo, path) as path,
			repos.repo,
			data,
			commit_hash,
			commit_date,
			last_modified,
			last_modified_commit,
			format_url('https://github.com/erc-dharma/%s/blob/%s/%s', repos.repo,
				commit_hash, path) as github_commit_url,
			format_url('https://github.com/erc-dharma/%s/blob/%s/%s', repos.repo,
				last_modified_commit, path) as github_last_modified_commit_url,
			repos.title as repo_title
		from documents
			join files on documents.name = files.name
			join repos on documents.repo = repos.repo
		where documents.name = ?""",
		(config.path_of("repos"), text)).fetchone()
	if not row:
		db.execute("rollback")
		return flask.abort(404)
	import parse_ins
	try:
		doc = parse_ins.process_file(row["path"], row["data"])
		title = doc.title and doc.title.render_logical() or []
		doc.title = title and title.split(document.PARA_SEP) or []
		editors = doc.editors and doc.editors.render_logical() or []
		doc.editors = editors and editors.split(document.PARA_SEP) or []
	except tree.Error as e:
		doc = document.Document()
		doc.valid = False
		doc.ident = text
	langs = doc.langs
	doc.langs = []
	for lang in langs:
		(lang,) = db.execute("select name from langs_list where id = ?", (lang,)).fetchone()
		doc.langs.append(lang)
	doc.repository = row["repo"]
	doc.commit_hash, doc.commit_date = row["commit_hash"], row["commit_date"]
	doc.last_modified = row["last_modified"]
	doc.last_modified_commit = row["last_modified_commit"]
	db.execute("rollback")
	return flask.render_template("inscription.tpl", doc=doc,
		github_commit_url=row["github_commit_url"],
		github_last_modified_commit_url=row["github_last_modified_commit_url"],
		repo_title=row["repo_title"],
		text=text)

def base_name_windows(path):
	i = len(path)
	while i > 0 and path[i - 1] != "\\":
		i -= 1
	return path[i:]

assert base_name_windows(r"C:\Users\john\Documents\file.txt") == "file.txt"

def patch_links(soup, attr):
	from urllib.parse import urlparse
	for link in soup.find_all(**{attr: True}):
		url = urlparse(link[attr])
		if url.scheme or url.netloc:
			# Assume this is a full URL
			continue
		if not url.path:
			# Assume this is just a fragment
			continue
		if not url.path.startswith("/"):
			url = url._replace(flask.url_for("display_text", text=url.path))
		if os.getenv("DHARMA_DEBUG"):
			url = url._replace(scheme="http", netloc="localhost:8023")
		else:
			url = url._replace(scheme="https", netloc="dharmalekha.info")
		link[attr] = url.geturl()

@app.post("/convert")
def convert_text():
	doc = flask.request.json
	path, data = doc["path"], doc["data"]
	base = os.path.basename(path)
	if base == path:
		# Oxygen gives us absolute paths, so we are probably given a
		# Windows-like path if we end up here. Ideally, we should send
		# platform infos in the convert.py script, but we did not
		# think to do that, and people are already using the code.
		base = base_name_windows(path)
	name = os.path.splitext(base)[0]
	import parse_ins
	doc = parse_ins.process_file(path, data)
	title = doc.title.render_logical()
	doc.title = title and title.split(document.PARA_SEP) or []
	editors = doc.editors.render_logical()
	doc.editors = editors and editors.split(document.PARA_SEP)
	html = flask.render_template("inscription.tpl", doc=doc, text=name)
	soup = BeautifulSoup(html, "html.parser")
	# HACK
	# Chrome doesn't attempt to fetch remote modules apparently, so we
	# just include the module contents in the html page. Would be better
	# not to use modules at all and just use raw includes, even if messier.
	script = soup.find("script", {"type": "module"})
	assert script
	with open(config.path_of("static/base.js")) as f:
		script.string = f.read()
	del script["src"]
	patch_links(soup, "href")
	patch_links(soup, "src")
	return str(soup)

@app.get("/bibliography/page/<int:page>")
@config.transaction("texts")
def display_biblio_page(page):
	db = config.db("texts")
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
		entries.append(biblio.format_entry(key, config.from_json(entry), loc=[], n=None))
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

def is_robot(email):
	return email in ("readme-bot@example.com", "github-actions@github.com")

@app.post("/github-event")
def handle_github():
	# XXX remove as much logic as possible from here
	js = flask.request.json
	if not js.get("commits"):
		return ""
	repo = js["repository"]["name"]
	# XXX remove special case, add hooks or something for each repo
	if repo != "tfd-nusantara-philology" and all(is_robot(commit["author"]["email"]) for commit in js["commits"]):
		return ""
	change.notify(repo)
	return ""

if __name__ == "__main__":
	app.run(host="localhost", port=8023, debug=True)
