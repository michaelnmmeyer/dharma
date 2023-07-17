#!/usr/bin/env python3

import os, json, sys
from datetime import datetime
from dharma import config, bottle, change, persons

GIT_DB = config.open_db("github-log")
GIT_DB.executescript("""
create table if not exists logs(
	date integer,
	data text
);
""")
TEXTS_DB = config.open_db("texts")
NGRAM_DB = config.open_db("ngram")

@bottle.get("/")
def index():
	(date,) = TEXTS_DB.execute("select strftime('%Y-%m-%d %H:%M', ?, 'auto', 'localtime')", (config.CODE_DATE,)).fetchone()
	return bottle.template("index.tpl", code_hash=config.CODE_HASH, code_date=date)

def is_robot(email):
	return email in ("readme-bot@example.com", "github-actions@github.com")

@bottle.get("/commit-log")
def show_commit_log():
	commits = []
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

@bottle.get("/parallels/verses")
def show_parallel_verses():
	verses = []
	for id, file, verse, text, count in NGRAM_DB.execute("""SELECT id, file, verse, orig, count
		FROM verses where count > 0
	"""):
		verses.append((id, file, verse, text.splitlines(), count))
	return bottle.template("verses.tpl", verses=verses)

@bottle.get("/parallels/verses/<id>")
def show_verse_parallels(id):
	loc = NGRAM_DB.execute("SELECT file, verse FROM verses where id = ?", (id,)).fetchone()
	if not loc:
		abort(404, "No such verse")
	loc = " ".join(loc)
	verses = []
	for id, file, verse, orig, coeff in NGRAM_DB.execute("""SELECT id, file, verse, orig, coeff
		FROM verses JOIN verses_jaccard ON id = id2 WHERE id1 = ? ORDER BY coeff DESC""", (id,)):
		verses.append((id, file, verse, orig.splitlines(), coeff))
	return bottle.template("verse_parallels.tpl", verses=verses, loc=loc)

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
