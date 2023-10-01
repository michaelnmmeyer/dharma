import os, sys, logging, sqlite3, json, subprocess
import icu

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

# Report exceptions within user functions on stderr. Otherwise we only get a
# message that says an exception was raised, without more info.
sqlite3.enable_callback_tracebacks(True)

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

# The point of this wrapper is to make sure we don't use functions that might
# mess with transactions and use the same logic everywhere e.g.
# db.execute("commit") instead of the (redundant) db.commit().
class DB:

	def __init__(self, conn):
		self._conn = conn

	def execute(self, *args, **kwargs):
		return self._conn.execute(*args, **kwargs)

	def create_function(self, *args, **kwargs):
		return self._conn.create_function(*args, **kwargs)

	# We don't begin/commit transactions implicitly, might be error-prone
	# and not clear enough. OTOH, we rollback transactions when an
	# exception happens and isn't catched, and we make sure that no
	# transaction is opened when the wrapped function is called and when it
	# returns.
	def transaction(self, f):
		def wrapper(*args, **kwargs):
			assert not self._conn.in_transaction
			try:
				ret = f(*args, **kwargs)
			except Exception:
				if self._conn.in_transaction:
					self.execute("rollback")
				raise
			assert not self._conn.in_transaction
			return ret
		return wrapper

# For seeing how different collations work, see:
# https://icu4c-demos.unicode.org/icu-bin/collation.html
COLLATOR = icu.Collator.createInstance()
# The following is for ignoring punctuation
COLLATOR.setAttribute(icu.UCollAttribute.ALTERNATE_HANDLING, icu.UCollAttributeValue.SHIFTED)

def collate(a, b):
	# HACK
	if a == "[]":
		if b == "[]":
			return 0
		return 1
	if b == "[]":
		return -1
	return COLLATOR.compare(a, b)

if os.path.basename(sys.argv[0]) == "server.py":
	READ_ONLY = True
else:
	READ_ONLY = False

def open_db(name, schema=None):
	if name == ":memory:":
		path = name
	else:
		conn = DBS.get(name)
		if conn:
			return conn
		path = db_path(name)
	# The python sqlite3 module messes with sqlite's transaction mechanism.
	# This is error-prone, we don't want that, thus we set
	# isolation_level=None. Likewise, db.executescript() is a mess, we only
	# use it for initialization code.
	# https://docs.python.org/3/library/sqlite3.html#transaction-control
	kwargs = {"detect_types": sqlite3.PARSE_DECLTYPES, "isolation_level": None}
	if READ_ONLY and name != "github":
		kwargs["uri"] = True
		path = f"file:{path}?mode=ro"
	conn = sqlite3.connect(path, **kwargs)
	conn.row_factory = sqlite3.Row
	conn.executescript(common_schema)
	conn.create_function("format_date", 1, format_date, deterministic=True)
	conn.create_collation("icu", collate)
	# Only
	if schema and os.path.basename(sys.argv[0]) != "server.py":
		conn.executescript(schema)
	assert not conn.in_transaction
	db = DB(conn)
	DBS[name] = db
	return db

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
