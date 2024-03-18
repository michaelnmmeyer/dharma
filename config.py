import os, sys, logging, sqlite3, json, subprocess, re, ssl, threading, time, functools
from urllib.parse import urlparse, quote
import icu

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

def path_of(*path_elems):
	return os.path.join(THIS_DIR, *path_elems)

HOST = "localhost"
PORT = 8023
DEBUG = bool(int(os.environ.get("DEBUG", 1)))
DBS_DIR = os.path.join(THIS_DIR, "dbs")
REPOS_DIR = os.path.join(THIS_DIR, "repos")
STATIC_DIR = os.path.join(THIS_DIR, "static")
LOGS_DIR = os.path.join(THIS_DIR, "logs")

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL)

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
	ret = time.localtime(int(obj))
	return time.strftime('%Y-%m-%d %H:%M', ret)

# Each thread has its own db objects
DBS = threading.local()

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

# Like the eponymous function in xslt
def normalize_space(s):
	s = s.strip()
	return re.sub(r"\s+", " ", s)

# For seeing how different collations work, see:
# https://icu4c-demos.unicode.org/icu-bin/collation.html
COLLATOR = icu.Collator.createInstance()
# The following is for ignoring punctuation
COLLATOR.setAttribute(icu.UCollAttribute.ALTERNATE_HANDLING, icu.UCollAttributeValue.SHIFTED)

def collate_icu(a, b):
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

def format_url(*args):
	if len(args) == 0:
		return ""
	ret = args[0]
	if len(args) > 1:
		ret = ret % args[1:]
	return quote(ret, safe="/:")

def open_db(name, schema=None):
	db = getattr(DBS, name, None)
	if db:
		return db
	path = db_path(name)
	# The python sqlite3 module messes with sqlite's transaction mechanism.
	# This is error-prone, we don't want that, thus we set
	# isolation_level=None. Likewise, db.executescript() is a mess, we only
	# use it for initialization code.
	# https://docs.python.org/3/library/sqlite3.html#transaction-control
	conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES,
		isolation_level=None)
	# We use "pragma query_only" instead of opening the db in read-only mode
	# because we want to be able to optimize the db at exit.
	if READ_ONLY and name == "texts":
		conn.execute("pragma query_only = yes")
	conn.row_factory = sqlite3.Row
	conn.executescript(common_schema)
	conn.create_function("format_date", 1, format_date, deterministic=True)
	conn.create_function("format_url", -1, format_url, deterministic=True)
	conn.create_collation("icu", collate_icu)
	db = DB(conn)
	setattr(DBS, name, db)
	return db

# We don't begin/commit transactions implicitly, might be error-prone
# and not clear enough. OTOH, we rollback transactions when an
# exception happens and isn't catched, and we make sure that no
# transaction is opened when the wrapped function is called and when it
# returns.
def transaction(db_name):
	def decorator(f):
		@functools.wraps(f)
		def decorated(*args, **kwargs):
			db = open_db(db_name)
			assert not db._conn.in_transaction
			try:
				ret = f(*args, **kwargs)
			except Exception:
				if db._conn.in_transaction:
					db.execute("rollback")
				raise
			assert not db._conn.in_transaction
			return ret
		return decorated
	return decorator

def json_converter(blob):
	return json.loads(blob.decode())

def json_adapter(obj):
	return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

sqlite3.register_converter("json", json_converter)
sqlite3.register_adapter(list, json_adapter)
sqlite3.register_adapter(dict, json_adapter)

def append_unique(items, item):
	if item in items:
		return
	items.append(item)
	return items

def command(*cmd, **kwargs):
	logging.info("run %s" % " ".join(cmd))
	kwargs.setdefault("capture_output", True)
	kwargs.setdefault("check", True)
	kwargs.setdefault("env", os.environ)
	ret = None
	try:
		ret = subprocess.run(cmd, encoding="UTF-8", **kwargs)
	except subprocess.CalledProcessError:
		if ret:
			logging.info(ret.stderr)
		raise
	return ret

def normalize_url(url):
	url = url.rstrip("/") # XXX might not work for some websites
	ret = urlparse(url)
	if ret.scheme == "http":
		# Supports SSL?
		try:
			ssl.get_server_certificate((ret.hostname, ret.port or 443))
			ret = ret._replace(scheme="https")
		except ConnectionRefusedError:
			pass
	return ret.geturl()
	# Could also check that the url actually works, and also use link
	# rel=canonical, but this is slow. Should keep track of all URLs and
	# systematically submit them to the Wayback machine.
