import os, logging, sqlite3, json

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

HOST = "0.0.0.0"
PORT = 8023
DEBUG = bool(os.environ.get("DEBUG", False))
DBS_DIR = os.path.join(THIS_DIR, "dbs")
REPOS_DIR = os.path.join(THIS_DIR, "repos")
STATIC_DIR = os.path.join(THIS_DIR, "static")

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL)

with open(os.path.join(THIS_DIR, "version.txt")) as f:
	CODE_HASH = f.readline().strip()
	CODE_DATE = int(f.readline().strip())

common_schema = """
pragma page_size = 16384;
pragma journal_mode = wal;
pragma synchronous = normal;
pragma foreign_keys = on;
"""

def open_db(name):
	path = os.path.join(DBS_DIR, name + ".sqlite")
	conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
	conn.row_factory = sqlite3.Row
	conn.executescript(common_schema)
	return conn

def json_converter(blob):
	return json.loads(blob.decode())

def json_adapter(obj):
	return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

sqlite3.register_converter("json", json_converter)
sqlite3.register_adapter(list, json_adapter)
sqlite3.register_adapter(dict, json_adapter)
