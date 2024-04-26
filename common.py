import os, sys, logging, sqlite3, json, subprocess, re, ssl, threading
import functools, traceback, unicodedata, socket
from urllib.parse import urlparse, quote
import icu # pip install PyICU

DHARMA_HOME = os.path.dirname(os.path.abspath(__file__))
os.environ["DHARMA_HOME"] = DHARMA_HOME # for subprocesses

def path_of(*path_elems):
	return os.path.join(DHARMA_HOME, *path_elems)

logging.basicConfig(level="INFO")

# Report exceptions within user functions on stderr. Otherwise we only get a
# message that says an exception was raised, without more info.
sqlite3.enable_callback_tracebacks(True)

def report_callback_error(e):
	print(f"Exception of type {e.exc_type} in object {e.object!r}",
		file=sys.stderr)
	print(f"Value: {e.exc_value!r}", file=sys.stderr)
	print(f"Message: {e.err_msg}", file=sys.stderr)
	if e.exc_traceback:
		traceback.print_tb(e.exc_traceback, file=sys.stderr)
	os._exit(1) # exits without raising a SystemExit exception

sys.unraisablehook = report_callback_error

# We can only have one transaction active per database object, so we allocate
# new database objects for each thread. In a given thread, there is no point
# allocating more than one database object, so we allocate just one, and create
# it on demand.
DBS = threading.local()

# The point of this wrapper is to make sure we don't use functions that might
# mess with transactions (conn.executescript() in particular is dangerous),
# and that we use the same logic everywhere e.g. db.execute("commit") instead
# of the (redundant) db.commit().
class DB:

	def __init__(self, conn):
		self._conn = conn
		self._protected = False

	def execute(self, sql, *args, **kwargs):
		# We should never do anything outside of an explicitly
		# opened transaction.
		assert self._protected
		assert self._conn.in_transaction or sql.startswith("begin")
		return self._conn.execute(sql, *args, **kwargs)

	def save_file(self, file):
		self.execute("""
			insert or replace into files(
				name, repo, path, mtime,
				last_modified_commit, last_modified, data)
			values(?, ?, ?, ?, ?, ?, ?)""",
			(file.name, file.repo, file.path, file.mtime, *file.last_modified, file.data))
		for git_name in file.owners:
			self.execute("""
				insert or ignore into owners(name, git_name)
				values(?, ?)""", (file.name, git_name))

	def load_file(self, name):
		row = self.execute("""
			select files.name as name,
				repo, path, mtime,
				last_modified_commit, last_modified, data,
				json_group_array(owners.git_name) as file_owners
			from files join owners on files.name = owners.name
			where files.name = ? group by owners.git_name""",
			(name,)).fetchone()
		if not name:
			raise Exception("not found")
		from dharma import texts #XXX circular import
		f = texts.File(row["repo"], row["path"])
		setattr(f, "_mtime", row["mtime"])
		setattr(f, "_last_modified", (row["last_modified_commit"], row["last_modified"]))
		setattr(f, "_data", row["data"])
		setattr(f, "_owners", json.loads(row["file_owners"]))
		return f

# We begin/end transactions around functions that are decorated with
# `@transaction`. We rollback transactions when an exception occurs and is not
# catched. Nesting transactions is not possible.
def transaction(db_name):
	def decorator(f):
		@functools.wraps(f)
		def decorated(*args, **kwargs):
			d = db(db_name)
			assert not d._protected
			assert not d._conn.in_transaction
			d._protected = True
			d.execute("begin")
			try:
				ret = f(*args, **kwargs)
				d.execute("commit")
			except Exception:
				if d._conn.in_transaction:
					d.execute("rollback")
				raise
			finally:
				d._protected = False
			assert not d._conn.in_transaction
			return ret
		return decorated
	return decorator

# Like the eponymous function in xslt
def normalize_space(s):
	s = s.strip()
	return re.sub(r"\s+", " ", s)

def normalize_text(s):
	if s is None:
		s = ""
	elif not isinstance(s, str):
		# Make sure matching doesn't work across array elements.
		s = "!!!!!".join(s)
	s = unicodedata.normalize("NFKD", s)
	s = "".join(c for c in s if not unicodedata.combining(c))
	s = s.casefold()
	s = s.replace("œ", "oe").replace("æ", "ae").replace("ß", "ss").replace("đ", "d")
	return unicodedata.normalize("NFC", s.strip())

# For seeing how different collations work, see:
# https://icu4c-demos.unicode.org/icu-bin/collation.html
COLLATOR = icu.Collator.createInstance()
# The following is for ignoring punctuation
COLLATOR.setAttribute(icu.UCollAttribute.ALTERNATE_HANDLING, icu.UCollAttributeValue.SHIFTED)

def collate_icu(a, b):
	# HACK the problem is that we are sorting by json fields and that
	# we must handle null values
	if a is None or a == "[]":
		if b is None or b == "[]":
			return 0
		return 1
	if b is None or b == "[]":
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

def read_only_db():
	if os.path.basename(sys.argv[0]) in ("change.py", "repos.py"):
		return False
	return True

# TODO use this instead:
# https://stackoverflow.com/questions/880530/can-modules-have-properties-the-same-way-that-objects-can
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
	conn.create_function("format_url", -1, format_url, deterministic=True)
	conn.create_function("jaccard", 2, jaccard, deterministic=True)
	conn.create_collation("icu", collate_icu)
	if name == "texts":
		with open(path_of("schema.sql")) as f:
			sql = f.read()
		if read_only_db():
			# Make sure we do not attempt to modify the database.
			# And only execute pragmas in the schema, not the
			# create table, etc. stuff.
			conn.execute("pragma query_only = true")
			for line in sql.splitlines():
				if line.lstrip().startswith("pragma "):
					conn.execute(line)
		else:
			conn.executescript(sql)
	ret = DB(conn)
	setattr(DBS, name, ret)
	return ret

def from_json(s):
	if isinstance(s, bytes):
		s = s.decode()
	return json.loads(s)

class JSONEncoder(json.JSONEncoder):

	def default(self, obj):
		return str(obj)

def to_json(obj):
	return json.dumps(obj, ensure_ascii=False, separators=(",", ":"),
		sort_keys=True, cls=JSONEncoder)

sqlite3.register_converter("json", from_json)
# Python has a default converter for "timestamp" which is not only deprecated
# but also expects to find something else than a single int in the column,
# probably because other sql databases use a dedicated format for that.
sqlite3.register_converter("timestamp", int)
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

def pandoc(text):
	return command("pandoc", "-fmarkdown", "-thtml", input=text).stdout

CODE_HASH, CODE_DATE = command("git", "show", "--no-patch", "--format=%H %at",
	"HEAD").stdout.strip().split()
CODE_DATE = int(CODE_DATE)

def normalize_url(url):
	url = url.rstrip("/") # XXX might not work for some websites
	# XXX too slow to do live, should use a cache
	return url
	ret = urlparse(url)
	if ret.scheme == "http":
		# Supports SSL?
		try:
			ssl.get_server_certificate((ret.hostname, ret.port or 443))
			ret = ret._replace(scheme="https")
		except (ConnectionRefusedError, socket.gaierror):
			pass
	return ret.geturl()
	# Could also check that the url actually works, and also use link
	# rel=canonical, but this is slow. Should keep track of all URLs and
	# systematically submit them to the Wayback machine.

def numberize(s, n):
	# Late import to avoid loading this big file if not necessary.
	from dharma import english
	match n:
		case str() if n.isdigit():
			if n.isdigit():
				n = int(n)
			else:
				n = 0
		case int():
			assert n >= 0
		case _:
			n = len(n)
	if n == 1:
		return s
	chunks = s.rsplit(None, 1)
	if len(chunks) == 1:
		head, tail = "", chunks[0]
	else:
		head, tail = chunks
	w = tail.casefold()
	if w in english.S:
		return s + "s"
	elif w in english.ES:
		return s + "es"
	elif w in english.IES:
		return s[:-1] + "ies"
	elif w in english.IDENT:
		return s
	pl = english.REST.get(w)
	if not pl:
		logging.error(f"cannot numberize term {s!r}")
		return s
	return head + tail[:1] + pl[1:]

def sentence_case(s):
	if not s:
		return ""
	t = s.split(None, 1)
	t[0] = t[0].capitalize()
	return " ".join(t)

def to_boolean(s, dflt):
	match s.lower():
		case "true" | "yes" | "on" | "1":
			return True
		case "false" | "no" | "off" | "0":
			return False
		case _:
			return dflt
