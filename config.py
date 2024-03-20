import os, sys, logging, sqlite3, json, subprocess, re, ssl, threading, time
import functools
from urllib.parse import urlparse, quote
import icu

DHARMA_HOME = os.path.dirname(os.path.abspath(__file__))
# Export it for subprocesses
os.environ["DHARMA_HOME"] = DHARMA_HOME

def path_of(*path_elems):
	return os.path.join(DHARMA_HOME, *path_elems)

REPOS_DIR = os.path.join(DHARMA_HOME, "repos")

logging.basicConfig(level="INFO")

# Report exceptions within user functions on stderr. Otherwise we only get a
# message that says an exception was raised, without more info.
sqlite3.enable_callback_tracebacks(True)

def format_date(obj):
	ret = time.localtime(int(obj))
	return time.strftime('%Y-%m-%d %H:%M', ret)

# Python's sqlite wrapper does not allow us to share database objects between
# threads, even though sqlite itself is OK with that. So we allocate new
# database objects for each thread. In a given thread, there is no point
# allocating more than one database object, so we allocate just one, and
# create it on demand.
DBS = threading.local()

# The point of this wrapper is to make sure we don't use functions that might
# mess with transactions, and that we use the same logic everywhere e.g.
# db.execute("commit") instead of the (redundant) db.commit().
class DB:

	def __init__(self, conn):
		self._conn = conn

	def execute(self, *args, **kwargs):
		return self._conn.execute(*args, **kwargs)

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

def format_url(*args):
	if len(args) == 0:
		return ""
	ret = args[0]
	if len(args) > 1:
		ret = ret % args[1:]
	return quote(ret, safe="/:")

def trigrams(s):
	return (s[i:i + 3] for i in range(len(s) - 3 + 1))

def jaccard(s1, s2):
	ngrams1 = set(trigrams(s1))
	ngrams2 = set(trigrams(s2))
	try:
		inter = len(ngrams1 & ngrams2)
		return inter / (len(ngrams1) + len(ngrams2) - inter)
	except ZeroDivisionError:
		return 0

def db(name):
	ret = getattr(DBS, name, None)
	if ret:
		return ret
	path = path_of("dbs", name + ".sqlite")
	# The python sqlite3 module messes with sqlite's transaction mechanism.
	# This is error-prone, we don't want that, thus we set
	# isolation_level=None. Likewise, db.executescript() is a mess, we only
	# use it for initialization code.
	# https://docs.python.org/3/library/sqlite3.html#transaction-control
	conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES,
		isolation_level=None)
	conn.row_factory = sqlite3.Row
	if os.path.basename(sys.argv[0]) != "change.py":
		conn.execute("pragma query_only = yes")
	conn.execute("pragma synchronous = normal")
	conn.execute("pragma foreign_keys = on")
	conn.execute("pragma secure_delete = off")
	conn.create_function("format_date", 1, format_date, deterministic=True)
	conn.create_function("format_url", -1, format_url, deterministic=True)
	conn.create_function("jaccard", 2, jaccard, deterministic=True)
	conn.create_collation("icu", collate_icu)
	ret = DB(conn)
	setattr(DBS, name, ret)
	return ret

# We don't begin/commit transactions implicitly, might be error-prone
# and not clear enough. OTOH, we rollback transactions when an
# exception happens and isn't catched, and we make sure that no
# transaction is opened when the wrapped function is called and when it
# returns.
def transaction(db_name):
	def decorator(f):
		@functools.wraps(f)
		def decorated(*args, **kwargs):
			d = db(db_name)
			assert not d._conn.in_transaction
			try:
				ret = f(*args, **kwargs)
			except Exception:
				if d._conn.in_transaction:
					d.execute("rollback")
				raise
			assert not d._conn.in_transaction
			return ret
		return decorated
	return decorator

def from_json(s):
	if isinstance(s, bytes):
		s = s.decode()
	return json.loads(s)

def to_json(obj):
	return json.dumps(obj, ensure_ascii=False, separators=(",", ":"),
		sort_keys=True)

sqlite3.register_converter("json", from_json)
sqlite3.register_adapter(list, to_json)
sqlite3.register_adapter(dict, to_json)

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

CODE_HASH, CODE_DATE = command("git", "show", "--no-patch", "--format=%H %at",
	"HEAD").stdout.strip().split()
CODE_DATE = int(CODE_DATE)

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
