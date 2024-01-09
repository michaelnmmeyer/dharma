import os, json, sys, unicodedata, hashlib, locale
from datetime import datetime
from dharma import config, bottle, change, people, ngrams, catalog, parse, validate, parse_ins, biblio, document

SCHEMA = """
begin;
create table if not exists logs(
	date integer,
	data text
);
commit;
"""
GIT_DB = config.open_db("github", SCHEMA)

TEXTS_DB = config.open_db("texts")
NGRAMS_DB = config.open_db("ngrams")

@bottle.get("/")
def index():
	(date,) = config.DUMMY_DB.execute("select format_date(?)", (config.CODE_DATE,)).fetchone()
	return bottle.template("index.tpl", code_hash=config.CODE_HASH, code_date=date)

def is_robot(email):
	return email in ("readme-bot@example.com", "github-actions@github.com")

# Legacy url
@bottle.get("/commit-log")
def show_commit_log():
	return bottle.redirect("/commits")

@bottle.get("/commits")
def show_commit_log():
	commits = []
	for (doc,) in GIT_DB.execute("select data from logs order by data ->> '$.repository.pushed_at' desc"):
		doc = json.loads(doc)
		ret = {}
		repo = os.path.basename(doc["repository"]["full_name"])
		push_date = doc["repository"]["pushed_at"]
		(push_date,) = config.DUMMY_DB.execute("select format_date(?)", (push_date,)).fetchone()
		for commit in doc["commits"]:
			if is_robot(commit["author"]["email"]):
				continue
			author = commit["author"].get("username") or commit["author"]["name"]
			author = people.plain_from_github(author)
			hash = commit["id"]
			url = commit["url"]
			commits.append({"repo": repo, "date": push_date, "author": author, "hash": hash, "url": url})
	return bottle.template("commits.tpl", commits=commits)

@bottle.get("/documentation")
def show_documentation():
	return bottle.template("documentation.tpl")

@bottle.get("/documentation/<name>")
def show_tei_doc(name):
	return bottle.static_file(name + ".html", root=config.path_of("schemas"))

@bottle.get("/texts")
@TEXTS_DB.transaction
def show_texts():
	conn = TEXTS_DB
	conn.execute("begin")
	(last_updated,) = conn.execute("select format_date(value) from metadata where key = 'last_updated'").fetchone()
	owner = bottle.request.query.owner
	severity = bottle.request.query.severity
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
	conn.execute("commit")
	return bottle.template("texts.tpl", last_updated=last_updated, texts=rows, authors=authors, owner=owner, severity=severity)

@bottle.get("/texts/<repo>/<hash>/<name>")
def show_text(repo, hash, name):
	conn = TEXTS_DB
	row = conn.execute("""
		select name, commits.repo, commit_hash, code_hash, status, path as xml_path, html_path,
			format_date(commit_date) as readable_commit_date
		from texts natural join files
			join commits on texts.repo = commits.repo
		where commits.repo = ? and name = ? and commit_hash = ?
	""", (repo, name, hash)).fetchone()
	if not row:
		bottle.abort(404, "Not found")
	url = f"https://github.com/erc-dharma/{row['repo']}/blob/{row['commit_hash']}/{row['xml_path']}"
	if row["status"] == validate.OK:
		return bottle.redirect(url)
	path = os.path.join(config.REPOS_DIR, row["repo"], row["xml_path"])
	return bottle.template("invalid-text.tpl", text=row, github_url=url, result=validate.file(path))

@bottle.get("/parallels")
@NGRAMS_DB.transaction
def show_parallels():
	NGRAMS_DB.execute("begin")
	(date,) = NGRAMS_DB.execute("""select format_date(value)
		from metadata where key = 'last_updated'""").fetchone()
	rows = NGRAMS_DB.execute("select * from sources where verses + hemistiches + padas > 0")
	NGRAMS_DB.execute("commit")
	return bottle.template("parallels.tpl", data=rows, last_updated=date)

parallels_types = {
	"verses": 1,
	"hemistiches": 2,
	"padas": 4,
}

@bottle.get("/parallels/texts/<text>/<category>")
def show_parallels_details(text, category):
	type = parallels_types[category]
	rows = NGRAMS_DB.execute("""
		select id, number, contents, parallels from passages
		where type = ? and file = ? and parallels > 0
	""", (type, text))
	return bottle.template("parallels_details.tpl", file=text, category=category, data=rows)

@bottle.get("/parallels/texts/<text>/<category>/<id:int>")
@NGRAMS_DB.transaction
def show_parallels_full(text, category, id):
	type = parallels_types[category]
	db = NGRAMS_DB
	db.execute("begin")
	ret = db.execute("""
		select number, contents from passages where type = ? and id = ?
		""", (type, id)).fetchone()
	if not ret:
		bottle.abort(404, "Not found")
	number, contents = ret
	rows = db.execute("""
		select file, number, contents, id2, coeff
		from passages join jaccard on passages.id = jaccard.id2
		where jaccard.type = ? and jaccard.id = ?
		order by coeff desc
	""", (type, id)).fetchall()
	db.execute("commit")
	return bottle.template("parallels_enum.tpl", category=category, file=text,
		number=number, data=rows, contents=contents)

@bottle.get("/catalog")
def show_catalog():
	q = bottle.request.query.q
	s = bottle.request.query.s
	rows, last_updated = catalog.search(q, s)
	return bottle.template("catalog.tpl", rows=rows, q=q, s=s, last_updated=last_updated, json=json)

@bottle.get("/langs")
def show_langs():
	rows = TEXTS_DB.execute("""
	select langs_list.inverted_name as name,
		json_group_array(distinct(langs_by_code.code)) as codes,
		printf('639-%d', iso) as iso
	from documents
		join json_each(documents.langs)
		join langs_list on langs_list.id = json_each.value
		join langs_by_code on langs_list.id = langs_by_code.id
	group by langs_list.id order by langs_list.inverted_name collate icu""").fetchall()
	return bottle.template("langs.tpl", rows=rows, json=json)

@bottle.get("/parallels/search")
def search_parallels():
	text = bottle.request.query.text
	orig_text = text
	type = bottle.request.query.type
	if not text or not type:
		return bottle.redirect("/parallels")
	text = unicodedata.normalize("NFC", text)
	page = bottle.request.query.page
	if page and page.isdigit():
		page = int(page)
		if page < 1:
			page = 1
	else:
		page = 1
	ret, formatted_text, page, per_page, total = ngrams.search(text, type, page)
	return bottle.template("parallels_search.tpl",
		data=ret, text=formatted_text,
		category=type,
		category_plural=type + (type == "hemistich" and "es" or "s"),
		page=page,
		per_page=per_page,
		orig_text=orig_text,
		total=total)

@bottle.get("/display")
def display_home():
	texts = [t for (t,) in TEXTS_DB.execute("select name from texts where name glob 'DHARMA_INS*'")]
	return bottle.template("display.tpl", texts=texts)

@bottle.get("/display/<text>")
@TEXTS_DB.transaction
def display_text(text):
	path, repo, commit_hash, commit_date, last_modified, github_url = TEXTS_DB.execute("""
		select
			printf('%s/%s/%s', ?, repo, path),
			repo,
			commit_hash,
			format_date(commit_date),
			format_date(last_modified),
			printf('https://github.com/erc-dharma/%s/blob/%s/%s', repo, commit_hash, path)
		from texts natural join files natural join commits
		where name = ?""",
		(config.REPOS_DIR, text)).fetchone() or (None, None)
	if not path:
		return bottle.abort(404, "Not found")
	import parse_ins
	doc = parse_ins.process_file(path, TEXTS_DB)
	doc.repository = repo
	doc.commit_hash, doc.commit_date = commit_hash, commit_date
	doc.last_modified = last_modified
	title = doc.title.render_logical()
	doc.title = title and title.split(document.PARA_SEP) or []
	editors = doc.editors.render_logical()
	doc.editors = editors and editors.split(document.PARA_SEP)
	sidebar = bottle.template("inscription-sidebar.tpl", doc=doc, text=text, numberize=parse.numberize)
	return bottle.template("inscription.tpl", doc=doc, github_url=github_url,
		text=text, numberize=parse.numberize, sidebar=sidebar)

@bottle.get("/test")
def test():
	return bottle.template("test.tpl")

@bottle.get("/bibliography/page/<page:int>")
@TEXTS_DB.transaction
def display_biblio(page):
	db = TEXTS_DB
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
	return bottle.template("biblio.tpl", page=page, pages_nr=pages_nr,
		entries=entries, entries_nr=entries_nr, per_page=biblio.PER_PAGE,
		first_entry=first_entry, last_entry=last_entry)

@bottle.get("/bibliography")
@TEXTS_DB.transaction
def display_biblio():
	return bottle.redirect("/bibliography/page/1")

@bottle.post("/validate/oxygen")
def do_validate():
	upload = bottle.request.files.get("upload")
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

@bottle.post("/github-event")
def handle_github():
	js = bottle.request.json
	doc = json.dumps(js, ensure_ascii=False, separators=(",", ":"))
	GIT_DB.execute("insert into logs values(strftime('%s', 'now'), ?)", (doc,))
	repo = js["repository"]["name"]
	if not js.get("commits"):
		return
	# XXX remove special case, add hooks or something for each repo
	if repo != "tfd-nusantara-philology" and all(is_robot(commit["author"]["email"]) for commit in js["commits"]):
		return
	change.notify(repo)

@bottle.get("/<filename:path>")
def handle_static(filename):
	ret = bottle.static_file(filename, root=config.STATIC_DIR)
	return ret

class ServerAdapter(bottle.ServerAdapter):
	log_file = None
	def run(self, handler):
		import socket
		from wsgiref.simple_server import make_server, WSGIServer, WSGIRequestHandler

		class Server(WSGIServer):

			def server_bind(self):
				self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
				super().server_bind()

		class Handler(WSGIRequestHandler):

			def _log(self, doc):
				req, res = bottle.request, bottle.response
				now = datetime.now()
				url = req.path
				if req.query_string:
					url += "?" + req.query_string
				doc.update({
					# the only reason we lowercase stuff and replace "-" is "_" is to make it
					# easier to query the results with jq.
					"remote": req.remote_addr,
					"date": now.strftime("%Y-%m-%d_%H:%M:%S"),
					"request": {
						"method": req.method,
						"url": url,
						"headers": {k.lower().replace("-","_"): v for k, v in req.headers.items()},
					},
					"response": {
						"status": res.status_code,
						"headers": {k.lower().replace("-","_"): v for k, v in res.headers.items()},
					},
				})
				doc = config.json_adapter(doc)
				print(doc, file=log_file)
				if not os.getenv("WITHIN_DOCKER"):
					print(doc, file=sys.stderr)

			def log_request(self, *args, **kwargs):
				self._log({})

			def log_message(self, format, *args):
				print(format, args)

			def log_exception(self, info):
				doc = config.json_adapter({
					"type": info[0],
					"value": info[1],
					"traceback": info[2],
				})
				self._log(doc)

		server = make_server(self.host, self.port, handler, server_class=Server, handler_class=Handler)

		try:
			os.mkdir(config.LOGS_DIR)
		except FileExistsError:
			pass
		log_file = open(os.path.join(config.LOGS_DIR, datetime.now().strftime("%Y-%m-%d") + ".txt"), "a")
		try:
			server.serve_forever()
		finally:
			print("Shutting down", file=sys.stderr)
			for name, db in config.DBS.items():
				# See https://www.sqlite.org/pragma.html#pragma_optimize
				# TODO also do that every few hours
				continue # XXX
				print("optimizing %r" % name, file=sys.stderr)
				db.execute("pragma query_only = yes")
				db.execute("pragma optimize")
			log_file.flush()
			log_file.close()
			server.server_close()

if __name__ == "__main__":
	bottle.run(host=config.HOST, port=config.PORT, debug=config.DEBUG,
		reloader=config.DEBUG, server=ServerAdapter)
