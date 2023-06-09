import os, sqlite3, json, socket
from datetime import datetime
from wsgiref.simple_server import WSGIServer
from dharma import bottle

if os.getenv("HOST") == "beta":
	# Production server
	BOTTLE_RELOAD = False
	DEBUG = False
else:
	BOTTLE_RELOAD = True
	DEBUG = True

DB_PATH = os.getenv("DB_PATH") or "github-log.sqlite"

DB = sqlite3.connect(DB_PATH)
DB.executescript("""
pragma journal_mode = wal;
pragma synchronous = normal;
create table if not exists logs(
	date integer,
	data text
);
""")

@bottle.route("/")
def index():
	return "Under construction\n"

@bottle.route("/commit-log")
def show_commit_log():
	commits = []
	for date, doc in DB.execute("select date, data from logs order by date desc"):
		doc = json.loads(doc)
		ret = {}
		repo = os.path.basename(doc["repository"]["full_name"])
		date = datetime.fromtimestamp(date).strftime("%d/%m/%y %H:%M")
		for commit in doc["commits"]:
			if commit["author"]["email"] == "github-actions@github.com":
				continue
			author = commit["author"]["username"]
			hash = commit["id"]
			url = commit["url"]
			commits.append({"repo": repo, "date": date, "author": author, "hash": hash, "url": url})
	return bottle.template("commit-log.tpl", commits=commits)

@bottle.post("/github-event")
def handle_github():
	doc = json.dumps(bottle.request.json, ensure_ascii=False, separators=(",", ":"))
	DB.execute("insert into logs values(strftime('%s', 'now'), ?)", (doc,))
	DB.commit()

class Server(WSGIServer):
	def server_bind(self):
		self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
		super().server_bind()

bottle.run(host="localhost", port=8023, debug=DEBUG, reloader=BOTTLE_RELOAD, server_class=Server)
