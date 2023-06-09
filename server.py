import os, sqlite3, json, socket
from wsgiref.simple_server import WSGIServer
from dharma import bottle

BOTTLE_RELOAD = True

if os.getenv("HOST") == "beta":
	# Production server
	BOTTLE_RELOAD = False
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
		doc = json.dumps(bottle.request.json, ensure_ascii=False, separators=(",", ":"))
		DB.execute("insert into logs values(strftime('%s', 'now'), ?)", (doc,))
		DB.commit()

@bottle.route("/")
def index():
	return "Under construction\n"

class Server(WSGIServer):
	def server_bind(self):
		self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
		super().server_bind()

bottle.run(host="localhost", port=8023, reloader=BOTTLE_RELOAD, server_class=Server)
