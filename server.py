import os, sqlite3, json
from dharma import bottle

if os.getenv("HOST") == "beta":
	DB = sqlite3.connect("github-log.sqlite")
	DB.executescript("""
	pragma journal_mode = wal;
	pragma synchronous = normal;
	create table if not exists logs(
		date integer,
		data text
	);
	""")
	@bottle.post("/github-event")
	def handle_github():
		doc = json.dumps(request.json, ensure_ascii=False, separators=(",", ":"))
		DB.execute("insert into logs values(strftime('%s', 'now'), ?)", (doc,))
		DB.commit()

@bottle.route("/")
def index():
	return "Under construction\n"

bottle.run(host="localhost", port=8023, reloader=True)
