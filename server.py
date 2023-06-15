import os, sqlite3, json, socket
from datetime import datetime
from wsgiref.simple_server import WSGIServer
from dharma import bottle

this_dir = os.path.dirname(os.path.abspath(__file__))

if os.getenv("HOST") == "beta":
	# Production server
	BOTTLE_RELOAD = False
	DEBUG = False
else:
	BOTTLE_RELOAD = True
	DEBUG = True

DB_PATH = os.getenv("DB_PATH") or os.path.join(this_dir, "github-log.sqlite")

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
	return bottle.template("index.tpl")

@bottle.route("/commit-log")
def show_commit_log():
	commits = []
	for date, doc in DB.execute("select date, data from logs order by date desc"):
		doc = json.loads(doc)
		ret = {}
		repo = os.path.basename(doc["repository"]["full_name"])
		date = datetime.fromtimestamp(date).strftime("%d/%m/%y %H:%M")
		for commit in doc["commits"]:
			if commit["author"]["email"] in ("github-actions@github.com", "readme-bot@example.com"):
				continue
			author = commit["author"]["username"]
			hash = commit["id"]
			url = commit["url"]
			commits.append({"repo": repo, "date": date, "author": author, "hash": hash, "url": url})
	return bottle.template("commit-log.tpl", commits=commits)

@bottle.route("/texts")
def show_texts():
	path = os.path.join(this_dir, "texts")
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
	path = os.path.join(this_dir, "texts", name)
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
