import os, sys, logging, sqlite3, json, subprocess

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

HOST = os.getenv("WITHIN_DOCKER") and "0.0.0.0" or "localhost"
PORT = 8023
DEBUG = bool(int(os.environ.get("DEBUG", 1)))
DBS_DIR = os.path.join(THIS_DIR, "dbs")
REPOS_DIR = os.path.join(THIS_DIR, "repos")
STATIC_DIR = os.path.join(THIS_DIR, "static")
LOGS_DIR = os.path.join(THIS_DIR, "logs")

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL)

DUMMY_DB = None

with open(os.path.join(THIS_DIR, "version.txt")) as f:
	CODE_HASH = f.readline().strip()
	CODE_DATE = int(f.readline().strip())

common_schema = """
pragma page_size = 16384;
pragma journal_mode = wal;
pragma synchronous = normal;
pragma foreign_keys = on;
pragma secure_delete = off;
"""

def db_path(name):
	return os.path.join(DBS_DIR, name + ".sqlite")

def format_date(obj):
	(ret,) = DUMMY_DB.execute("select strftime('%Y-%m-%d %H:%M', ?, 'auto', 'localtime')", (obj,)).fetchone()
	return ret

DBS = {}

def open_db(name):
	if name == ":memory:":
		path = name
	else:
		conn = DBS.get(name)
		if conn:
			return conn
		path = db_path(name)
	conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
	conn.row_factory = sqlite3.Row
	conn.executescript(common_schema)
	conn.create_function("format_date", 1, format_date, deterministic=True)
	DBS[name] = conn
	return conn

DUMMY_DB = open_db(":memory:")

def json_converter(blob):
	return json.loads(blob.decode())

def json_adapter(obj):
	return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

sqlite3.register_converter("json", json_converter)
sqlite3.register_adapter(list, json_adapter)
sqlite3.register_adapter(dict, json_adapter)

def command(*cmd, **kwargs):
	print(*cmd, file=sys.stderr)
	kwargs.setdefault("capture_output", True)
	kwargs.setdefault("check", True)
	ret = None
	try:
		ret = subprocess.run(cmd, encoding="UTF-8", **kwargs)
	except subprocess.CalledProcessError:
		if ret:
			sys.stderr.write(ret.stderr)
			sys.stderr.flush()
		raise
	return ret
