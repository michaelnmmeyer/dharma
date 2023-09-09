#!/usr/bin/env python3

import os, json, sys, unicodedata
from datetime import datetime
from dharma import config, bottle, change, persons, ngrams

GIT_DB = config.open_db("github-log")
GIT_DB.executescript("""
create table if not exists logs(
	date integer,
	data text
);
""")
TEXTS_DB = config.open_db("texts")
NGRAMS_DB = config.open_db("ngrams")

@bottle.get("/")
def index():
	(date,) = TEXTS_DB.execute("select strftime('%Y-%m-%d %H:%M', ?, 'auto', 'localtime')", (config.CODE_DATE,)).fetchone()
	return bottle.template("index.tpl", code_hash=config.CODE_HASH, code_date=date)

def is_robot(email):
	return email in ("readme-bot@example.com", "github-actions@github.com")

@bottle.get("/commit-log")
def show_commit_log():
	commits = []
	# FIXME sort by the actual push date
	for (doc,) in GIT_DB.execute("select data from logs order by date desc"):
		doc = json.loads(doc)
		ret = {}
		repo = os.path.basename(doc["repository"]["full_name"])
		push_date = doc["repository"]["pushed_at"]
		(push_date,) = TEXTS_DB.execute("select strftime('%Y-%m-%d %H:%M', ?, 'auto', 'localtime')", (push_date,)).fetchone()
		for commit in doc["commits"]:
			if is_robot(commit["author"]["email"]):
				continue
			author = commit["author"].get("username") or commit["author"]["name"]
			author = persons.plain_from_github(author)
			hash = commit["id"]
			url = commit["url"]
			commits.append({"repo": repo, "date": push_date, "author": author, "hash": hash, "url": url})
	return bottle.template("commit-log.tpl", commits=commits)

@bottle.get("/texts")
def show_texts():
	conn = TEXTS_DB
	conn.execute("begin")
	(last_updated,) = conn.execute("""
		select strftime('%Y-%m-%d %H:%M', max(when_validated), 'auto', 'localtime')
		from validation
	""").fetchone()
	owner = bottle.request.query.owner
	if owner:
		rows = list(conn.execute("""
			select name, validation.repo, commit_hash,
				strftime('%Y-%m-%d %H:%M', commit_date, 'auto', 'localtime') as readable_commit_date,
				valid, html_path
			from owners join latest_commits on owners.repo = latest_commits.repo
				natural join validation natural join texts
			where author_id = ? order by name""", (owner,)))
	else:
		rows = list(conn.execute("""
			select name, repo, commit_hash,
				strftime('%Y-%m-%d %H:%M', commit_date, 'auto', 'localtime') as readable_commit_date,
				valid, html_path
			from latest_commits natural join validation natural join texts
			order by name"""))
	authors = []
	for (author_id,) in conn.execute("select distinct author_id from owners"):
		authors.append((author_id, persons.plain(author_id)))
	conn.execute("commit")
	return bottle.template("texts.tpl", last_updated=last_updated, texts=rows, authors=authors, owner=owner)

@bottle.get("/texts/<repo>/<hash>/<name>")
def show_text(repo, hash, name):
	conn = TEXTS_DB
	row = conn.execute("""
		select name, repo, commit_hash, code_hash, errors, xml_path, html_path,
			strftime('%Y-%m-%d %H:%M', commit_date, 'auto', 'localtime') as readable_commit_date,
			strftime('%Y-%m-%d %H:%M', when_validated, 'auto', 'localtime') as readable_when_validated
		from validation natural join commits natural join texts
		where repo = ? and name = ? and commit_hash = ?
	""", (repo, name, hash)).fetchone()
	if not row:
		bottle.abort(404, "Not found")
	url = f"https://github.com/erc-dharma/{row['repo']}/blob/{row['commit_hash']}/{row['xml_path']}"
	if row["errors"]:
		return bottle.template("invalid-text.tpl", text=row, github_url=url)
	bottle.redirect(url)

@bottle.get("/parallels")
def show_parallels():
	(date,) = NGRAMS_DB.execute("""select strftime('%Y-%m-%d %H:%M', value, 'auto', 'localtime')
		from metadata where key = 'last_modified'""").fetchone()
	rows = NGRAMS_DB.execute("select * from sources where verses + hemistiches + padas > 0")
	return bottle.template("parallels.tpl", data=rows, last_modified=date)

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
def show_parallels_full(text, category, id):
	type = parallels_types[category]
	NGRAMS_DB.execute("begin")
	number, contents = NGRAMS_DB.execute("""
		select number, contents from passages where type = ? and id = ?
		""", (type, id)).fetchone()
	rows = NGRAMS_DB.execute("""
		select file, number, contents, id2, coeff
		from passages join jaccard on passages.id = jaccard.id2
		where jaccard.type = ? and jaccard.id = ?
		order by coeff desc
	""", (type, id)).fetchall()
	NGRAMS_DB.execute("commit")
	return bottle.template("parallels_enum.tpl", category=category, file=text,
		number=number, data=rows, contents=contents)

@bottle.get("/parallels/search")
def search_parallels():
	text = bottle.request.query.text
	type = bottle.request.query.type
	if not text or not type:
		return bottle.redirect("/parallels")
	text = unicodedata.normalize("NFC", text)
	ret, formatted_text = ngrams.search(text, type)
	return bottle.template("parallels_search.tpl",
		data=ret, text=formatted_text,
		category=type + (type == "hemistich" and "es" or "s"))

@bottle.get("/parallels/verses")
def redirect_parallels():
	bottle.redirect("/parallels")

@bottle.post("/github-event")
def handle_github():
	js = bottle.request.json
	doc = json.dumps(js, ensure_ascii=False, separators=(",", ":"))
	GIT_DB.execute("insert into logs values(strftime('%s', 'now'), ?)", (doc,))
	GIT_DB.commit()
	if all(is_robot(commit["author"]["email"]) for commit in js["commits"]):
		return
	repo = js["repository"]["name"]
	change.notify(repo)

@bottle.get("/<filename:path>")
def handle_static(filename):
	return bottle.static_file(filename, root=config.STATIC_DIR)

class ServerAdapter(bottle.ServerAdapter):
	def run(self, handler):
		import socket
		from wsgiref.simple_server import make_server, WSGIServer
		class Server(WSGIServer):
			def server_bind(self):
				self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
				super().server_bind()
		server = make_server(self.host, self.port, handler, server_class=Server)
		try:
			server.serve_forever()
		finally:
			print("Shutting down", file=sys.stderr)
			server.server_close()

if __name__ == "__main__":
	bottle.run(host=config.HOST, port=config.PORT, debug=config.DEBUG,
		reloader=config.DEBUG, server=ServerAdapter)
