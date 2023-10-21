# When processing a text, oxygen generates zotero API calls like this:
# https://api.zotero.org/groups/1633743/items?tag=ROD1914&format=tei
# This is why tags are used, but can we generate another API call that uses a
# proper primary key? Yes, use:
# https://api.zotero.org/groups/1633743/items/ZZH5G8PB?format=tei

import sys, io, json, unicodedata, html, re, time
import requests
from xml.parsers import expat
from dharma import config, tree

LIBRARY_ID = 1633743
MY_API_KEY = "ojTBU4SxEQ4L0OqUhFVyImjq"

SCHEMA = """
begin;
create table if not exists meta(
	key text primary key not null,
	value
);
insert or ignore into meta values('latest_version', 0);

create table if not exists bibliography(
	key text primary key not null,
	version integer not null,
	json json not null check(json_valid(json)),
	short_title as (json ->> '$.data.shortTitle')
);
commit;
"""
db = config.open_db("biblio", SCHEMA)

def zotero_items(max_version, ret):
	s = requests.Session()
	s.headers["Zotero-API-Version"] = "3"
	s.headers["Zotero-API-Key"] = MY_API_KEY
	r = s.get(f"https://api.zotero.org/groups/{LIBRARY_ID}/items?since={max_version}")
	latest_version = 0
	while True:
		wait = max( # in seconds
			0,
			int(r.headers.get("Backoff", 0)),
			int(r.headers.get("Retry-After", 0)))
		if r.status_code != 200:
			if not wait or wait > 20:
				# Will try later.
				latest_version = max_version
				break
		new_version = int(r.headers["Last-Modified-Version"])
		if not latest_version:
			latest_version = new_version
		entries = r.json()
		assert isinstance(entries, list)
		for entry in entries:
			if entry["version"] > latest_version:
				continue
			yield entry
		next = re.search(r'<([^>]+)>;\s*rel="next"', r.headers.get("Link", ""))
		if not next:
			break
		time.sleep(wait)
		r = s.get(next.group(1))
	ret.append(latest_version)

@db.transaction
def update():
	db.execute("begin")
	(max_version,) = db.execute("select value from meta where key = 'latest_version'").fetchone()
	ret = []
	for entry in zotero_items(max_version, ret):
		db.execute("""insert or replace into bibliography(key, version, json)
			values(?, ?, ?)""", (entry["key"], entry["version"], entry))
	assert len(ret) == 1
	db.execute("update meta set value = ? where key = 'latest_version'", tuple(ret))
	db.execute("commit")

# See https://www.zotero.org/support/kb/rich_text_bibliography
valid_tags = {
	"i": [],
	"b": [],
	"sub": [],
	"sup": [],
	"span": [("style", "font-variant:small-caps;"), ("class", "nocase")],
}

ident_like = {"shortTitle", "tags", "key", "url", "links"}

def all_string_values(obj, ignore):
	if isinstance(obj, str):
		yield obj
	elif isinstance(obj, int):
		pass
	elif obj is None:
		pass
	elif isinstance(obj, list):
		for val in obj:
			yield from all_string_values(val, ignore)
	else:
		assert isinstance(obj, dict), obj
		for k, v in obj.items():
			if k in ignore:
				continue
			yield from all_string_values(v, ignore)

def check_string_value(xml, entry):
	for tag in xml.find(".//em"):
		tag.name = "i"
	for tag in xml.find(".//a"):
		assert "href" in tag.attrs
		href = tag["href"]
		tag.attrs.clear()
		tag["href"] = href
	for tag in xml.find(".//*"):
		if tag.name == "a":
			continue # special case
		attrs = valid_tags.get(tag.name)
		ok = True
		if attrs is None:
			ok = False
		elif len(tag.attrs) > 1 or (attrs and not tag.attrs):
			ok = False
		elif attrs and not list(tag.attrs.items())[0] in attrs:
			ok = False
		if not ok:
			tag.unwrap()

def check_entries():
	for (entry,) in db.execute("select json from bibliography"):
		for val in all_string_values(entry, ignore=set()):
			fix_string(val)

def fix_string(val):
	val = unicodedata.normalize("NFC", val)
	val = html.unescape(val)
	val = val.replace("&", "&amp;")
	val = "<root>%s</root>" % val
	try:
		xml = tree.parse_string(val).root
		check_string_value(xml, entry)
		val = xml.xml()[len("<root>"):-len("</root>")]
	except expat.ExpatError:
		val = html.escape(val)
	return val

class Writer:

	def __init__(self):
		self.buf = ""

	def add_space(self):
		if self.buf and not self.buf[-1].isspace():
			self.write(" ")

	def add_period(self): # TODO take tags into account
		i = len(self.buf)
		while i > 0:
			i -= 1
			c = self.buf[i]
			if c == ".":
				return
			if c.isalpha() or c.isdigit():
				break
		self.buf += "."

	def write(self, s):
		self.buf += s

	def write_names(self, authors):
		if not authors:
			return
		for i, author in enumerate(authors):
			if i == 0:
				self.write("%s, %s" % (author["lastName"], author["firstName"]))
				continue
			if i == len(authors) - 1:
				self.write(" and ")
			else:
				self.write(", ")
			self.write("%s %s" % (author["firstName"], author["lastName"]))
		self.add_period()

	def write_date(self, date):
		if not date:
			return
		self.add_space()
		self.write(date)
		self.add_period()

	def write_quoted(self, title):
		if not title:
			return
		self.add_space()
		self.write("“")
		self.write(title)
		self.add_period()
		self.write("”")

	def write_italic(self, title):
		if not title:
			return
		self.add_space()
		self.write("<i>")
		self.write(title)
		self.write("</i>")
		self.add_period()

	def end(self):
		pass

def render_journal_article(rec, w, params):
	w.write_names(rec["creators"])
	w.write_date(rec["date"])
	w.write_quoted(rec["title"])
	if rec["publicationTitle"]:
		w.add_space()
		w.write("<i>")
		w.write(rec["publicationTitle"])
		w.write("</i>")
		if rec["volume"]:
			w.add_space()
			w.write(rec["volume"])
		if rec["pages"]:
			w.write(":")
			w.add_space()
			w.write(rec["pages"])
		for unit, abbr in (("page", "p."), ("appendix", "appendix"), ("item", "№")):
			val = params.get(unit)
			if val:
				w.write(", ")
				w.write(abbr + "\N{NBSP}")
				w.write(val)
		w.add_period()

# See
# https://github.com/zotero/translators/blob/master/TEI.js
def render_book(rec, w, params):
	w.write_names(rec["creators"])
	w.write_date(rec["date"])
	w.write_italic(rec["title"])
	if rec["series"]:
		w.add_space()
		w.write(rec["series"])
		if rec["seriesNumber"]:
			w.write(" %s" % rec["seriesNumber"])
		w.write(".")
	if rec["place"]:
		w.add_space()
		w.write(rec["place"])
		if rec["publisher"]:
			w.write(": %s" % rec["publisher"])
		for unit, abbr in (("page", "p."), ("appendix", "appendix"), ("item", "nº")):
			val = params.get(unit)
			if val:
				w.write(", ")
				w.write(abbr + "\N{NBSP}")
				w.write(val)
		w.add_period()

renderers = {
	"book": render_book,
	"journalArticle": render_journal_article,
}

def render(rec, params):
	f = renderers.get(rec["itemType"])
	if not f:
		return
	w = Writer()
	f(rec, w, params)
	w.end()
	return w.buf

def make_ref(rec, omit_name):
	if omit_name:
		return rec["date"]
	authors = rec["creators"]
	if not authors:
		return
	author = authors[0]
	buf = author["lastName"]
	if len(authors) == 1:
		pass
	elif len(authors) == 2:
		buf += " and " + authors[1]["lastName"]
	elif len(authors) >= 3:
		buf += " <i>et al.</i>"
	buf += " " + rec["date"]
	return buf

# TODO complain when multiple entries
def get_entry(ref, params):
	recs = db.execute("select key, json from bibliography where short_title = ?", (ref,)).fetchall()
	if not recs:
		return "???", ""
	key, ret = recs[0]
	ret = render(ret["data"], params)
	return key, ret or ""

# TODO complain when multiple entries
def get_ref(ref, omit_name):
	recs = db.execute("select key, json from bibliography where short_title = ?", (ref,)).fetchall()
	if not recs:
		return "???", ""
	key, ret = recs[0]
	ret = make_ref(ret["data"], omit_name)
	return key, ret or ""

if __name__ == "__main__":
	print(get_entry(sys.argv[1]))
