#!/usr/bin/env python3

import os, sqlite3, json, sys
from datetime import datetime

from dharma import config, bottle, change

GIT_DB = sqlite3.connect(os.path.join(config.DB_DIR, "github-log.sqlite"))
GIT_DB.executescript("""
pragma journal_mode = wal;
pragma synchronous = normal;
create table if not exists logs(
	date integer,
	data text
);
""")

NGRAM_DB = sqlite3.connect(os.path.join(config.DB_DIR, "ngram.sqlite"))

@bottle.route("/")
def index():
	return bottle.template("index.tpl")

@bottle.route("/commit-log")
def show_commit_log():
	commits = []
	for date, doc in GIT_DB.execute("select date, data from logs order by date desc"):
		doc = json.loads(doc)
		ret = {}
		repo = os.path.basename(doc["repository"]["full_name"])
		date = datetime.fromtimestamp(date).strftime("%d/%m/%y %H:%M")
		for commit in doc["commits"]:
			if commit["author"]["email"] in ("github-actions@github.com", "readme-bot@example.com"):
				continue
			if not "username" in commit["author"]:
				continue
			author = commit["author"]["username"]
			hash = commit["id"]
			url = commit["url"]
			commits.append({"repo": repo, "date": date, "author": author, "hash": hash, "url": url})
	return bottle.template("commit-log.tpl", commits=commits)

@bottle.route("/texts")
def show_texts():
	path = os.path.join(config.this_dir, "texts")
	texts = []
	files = os.listdir(path)
	files.sort()
	err = False
	for f in files:
		name, ext = os.path.splitext(f)
		if ext == ".err":
			err = True
			continue # the xml comes just after this one
		elif ext == ".xml":
			texts.append((name, err))
			err = False
		else:
			assert 0
	return bottle.template("texts.tpl", texts=texts)

@bottle.route("/texts/<name>")
def show_text(name):
	path = os.path.join(config.this_dir, "texts", name)
	if os.path.abspath(path) != path:
		abort(400, "Fishy request")
	if not os.path.exists(path + ".xml"):
		abort(404, "Not found")
	try:
		with open(path + ".err") as f:
			errs = []
			for line in f:
				line = line.rstrip()
				fields = line.split(":", 2)
				errs.append(fields)
	except FileNotFoundError:
		errs = None
	if errs:
		return bottle.template("invalid-text.tpl", errors=errs, text_id=name)
	return bottle.static_file(path + ".xml", root="/")

@bottle.route("/parallels/verses")
def show_parallel_verses():
	verses = []
	for id, file, verse, text, count in NGRAM_DB.execute("""SELECT id, file, verse, orig, count
		FROM verses where count > 0
	"""):
		verses.append((id, file, verse, text.replace("\n", "<br/>"), count))
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
		verses.append((id, file, verse, orig.replace("\n", "<br/>"), coeff))
	return bottle.template("verse_parallels.tpl", verses=verses, loc=loc)

@bottle.post("/github-event")
def handle_github():
	js = bottle.request.json
	doc = json.dumps(js, ensure_ascii=False, separators=(",", ":"))
	GIT_DB.execute("insert into logs values(strftime('%s', 'now'), ?)", (doc,))
	GIT_DB.commit()
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
		reloader=not config.DEBUG, server=ServerAdapter)
