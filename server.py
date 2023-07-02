#!/usr/bin/env python3

import os, sqlite3, json, sys
from datetime import datetime
from dharma import config, bottle, change

sqlite3.register_converter("json", lambda d: json.loads(d.decode()))

GIT_DB = sqlite3.connect(os.path.join(config.DBS_DIR, "github-log.sqlite"))
GIT_DB.executescript("""
pragma journal_mode = wal;
pragma synchronous = normal;
create table if not exists logs(
	date integer,
	data text
);
""")

TEXTS_DB = sqlite3.connect(
	os.path.join(config.DBS_DIR, "texts.sqlite"),
	detect_types=sqlite3.PARSE_DECLTYPES)
TEXTS_DB.row_factory = sqlite3.Row

NGRAM_DB = sqlite3.connect(os.path.join(config.DBS_DIR, "ngram.sqlite"))

@bottle.route("/")
def index():
	return bottle.template("index.tpl", code_hash=config.CODE_HASH)

def is_robot(email):
	return email in ("readme-bot@example.com", "github-actions@github.com")

@bottle.route("/commit-log")
def show_commit_log():
	commits = []
	for (doc,) in GIT_DB.execute("select data from logs order by date desc"):
		doc = json.loads(doc)
		ret = {}
		repo = os.path.basename(doc["repository"]["full_name"])
		push_date = doc["repository"]["pushed_at"]
		push_date = datetime.fromtimestamp(push_date).strftime("%d/%m/%y %H:%M")
		for commit in doc["commits"]:
			if is_robot(commit["author"]["email"]):
				continue
			author = commit["author"].get("username") or commit["author"]["name"]
			hash = commit["id"]
			url = commit["url"]
			commits.append({"repo": repo, "date": push_date, "author": author, "hash": hash, "url": url})
	return bottle.template("commit-log.tpl", commits=commits)

@bottle.route("/texts")
def show_texts():
	conn = TEXTS_DB
	conn.execute("begin")
	(last_updated,) = conn.execute("""
		select strftime('%Y-%m-%d %H:%M', max(when_validated), 'auto', '+2 hours')
		from validation
	""").fetchone()
	rows = list(conn.execute("""
		select name, repo, commit_hash, strftime('%Y-%m-%d %H:%M', commit_date, 'auto', '+2 hours') as readable_commit_date,
			valid, html_path
		from latest_commits natural join validation natural join texts
		order by name"""))
	conn.execute("commit")
	return bottle.template("texts.tpl", last_updated=last_updated, texts=rows)

@bottle.route("/texts/<repo>/<hash>/<name>")
def show_text(repo, hash, name):
	conn = TEXTS_DB
	row = conn.execute("""
		select name, repo, commit_hash, code_hash, errors, xml_path, html_path,
			strftime('%Y-%m-%d %H:%M', commit_date, 'auto', '+2 hours') as readable_commit_date,
			strftime('%Y-%m-%d %H:%M', when_validated, 'auto', '+2 hours') as readable_when_validated
		from validation natural join commits natural join texts
		where repo = ? and name = ? and commit_hash = ?
	""", (repo, name, hash)).fetchone()
	if not row:
		bottle.abort(404, "Not found")
	url = f"https://github.com/erc-dharma/{row['repo']}/blob/{row['commit_hash']}/{row['xml_path']}"
	if row["errors"]:
		return bottle.template("invalid-text.tpl", text=row, github_url=url)
	bottle.redirect(url)

@bottle.route("/parallels/verses")
def show_parallel_verses():
	verses = []
	for id, file, verse, text, count in NGRAM_DB.execute("""SELECT id, file, verse, orig, count
		FROM verses where count > 0
	"""):
		verses.append((id, file, verse, text.splitlines(), count))
	return bottle.template("verses.tpl", verses=verses)

@bottle.route("/parallels/verses/<id>")
def show_verse_parallels(id):
	loc = NGRAM_DB.execute("SELECT file, verse FROM verses where id = ?", (id,)).fetchone()
	if not loc:
		abort(404, "No such verse")
	loc = " ".join(loc)
	verses = []
	for id, file, verse, orig, coeff in NGRAM_DB.execute("""SELECT id, file, verse, orig, coeff
		FROM verses JOIN verses_jaccard ON id = id2 WHERE id1 = ? ORDER BY coeff DESC""", (id,)):
		print((id, file, verse, orig.splitlines(), coeff))
	exit()
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
