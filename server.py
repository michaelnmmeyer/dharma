import os, json, sys, unicodedata, hashlib
from datetime import datetime
from dharma import config, bottle, change, people, ngrams, catalog, parse

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
TEXTS_DB.execute("attach database ? as people", (config.db_path("people"),))
NGRAMS_DB = config.open_db("ngrams")
LANGS_DB = config.open_db("langs")

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
	return bottle.template("commit-log.tpl", commits=commits)

@bottle.get("/documentation")
def show_documentation():
	return bottle.template("documentation.tpl")

@bottle.get("/documentation/<name>")
def show_tei_doc(name):
	return bottle.static_file(name + ".html", root=os.path.join(config.THIS_DIR, "schemas"))

@bottle.get("/texts")
@TEXTS_DB.transaction
def show_texts():
	conn = TEXTS_DB
	conn.execute("begin")
	(last_updated,) = conn.execute("select format_date(value) from metadata where key = 'last_updated'").fetchone()
	owner = bottle.request.query.owner
	if owner:
		rows = conn.execute("""
			select texts.name, texts.repo, commit_hash,
				format_date(commit_date) as readable_commit_date, valid
			from texts natural join validation
				join owners on texts.name = owners.name
				join commits on texts.repo = commits.repo
				join people_github on owners.git_name = people_github.git_name
			where dh_id = ? and not valid
			order by texts.name""", (owner,)).fetchall() # BUG
	else:
		rows = conn.execute("""
			select name, repo, commit_hash,
				format_date(commit_date) as readable_commit_date, valid
			from commits natural join validation natural join texts
			where not valid
			order by name""").fetchall()
	authors = conn.execute("""
		select distinct dh_id, print_name
		from people_main natural join people_github
			join owners on people_github.git_name = owners.git_name
		order by print_name""").fetchall()
	conn.execute("commit")
	return bottle.template("texts.tpl", last_updated=last_updated, texts=rows, authors=authors, owner=owner)

@bottle.get("/texts/<repo>/<hash>/<name>")
def show_text(repo, hash, name):
	conn = TEXTS_DB
	row = conn.execute("""
		select name, commits.repo, commit_hash, code_hash, errors, path as xml_path, html_path,
			format_date(commit_date) as readable_commit_date,
			format_date(when_validated) as readable_when_validated
		from texts natural join files
			natural join validation
			join commits on texts.repo = commits.repo
		where commits.repo = ? and name = ? and commit_hash = ?
	""", (repo, name, hash)).fetchone()
	if not row:
		bottle.abort(404, "Not found")
	url = f"https://github.com/erc-dharma/{row['repo']}/blob/{row['commit_hash']}/{row['xml_path']}"
	if row["errors"]:
		return bottle.template("invalid-text.tpl", text=row, github_url=url)
	bottle.redirect(url)

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
	rows = LANGS_DB.execute("""
	select list.inverted_name as name,
		json_group_array(distinct(by_code.code)) as codes,
		printf('639-%d', iso) as iso
	from catalog.documents
		join json_each(catalog.documents.langs)
		join list on list.id = json_each.value
		join by_code on list.id = by_code.id
	group by list.id order by list.inverted_name collate icu""").fetchall()
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
def display_text(text):
	(path,) = TEXTS_DB.execute("""select printf('%s/%s/%s', ?, repo, path) from texts natural join files
		where name = ?""",
		(config.REPOS_DIR, text)).fetchone() or (None,)
	if not path:
		return bottle.abort(404, "Not found")
	import parse_ins
	doc = parse_ins.process_file(path)
	doc.title = doc.title.render_physical().split(parse.PARA_SEP)
	doc.editors = doc.editors.render_physical().split(parse.PARA_SEP)
	return bottle.template("display_ins.tpl", doc=doc, text=text, numberize=parse.numberize)

@bottle.get("/test")
def test():
	return bottle.template("test.tpl")

# Legacy url
@bottle.get("/parallels/verses")
def redirect_parallels():
	bottle.redirect("/parallels")

@bottle.post("/github-event")
def handle_github():
	js = bottle.request.json
	doc = json.dumps(js, ensure_ascii=False, separators=(",", ":"))
	GIT_DB.execute("insert into logs values(strftime('%s', 'now'), ?)", (doc,))
	if all(is_robot(commit["author"]["email"]) for commit in js["commits"]):
		return
	repo = js["repository"]["name"]
	change.notify(repo)

@bottle.get("/<filename:path>")
def handle_static(filename):
	ret = bottle.static_file(filename, root=config.STATIC_DIR)
	#ret._headers["ETag"] = hashlib.md5(ret._headers["Last-Modified"][0].encode()).hexdigest()
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
			log_file.flush()
			log_file.close()
			server.server_close()

if __name__ == "__main__":
	bottle.run(host=config.HOST, port=config.PORT, debug=config.DEBUG,
		reloader=config.DEBUG, server=ServerAdapter)
