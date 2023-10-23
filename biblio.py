# When processing a text, oxygen generates zotero API calls like this:
# https://api.zotero.org/groups/1633743/items?tag=ROD1914&format=tei
# This is why tags are used, but can we generate another API call that uses a
# proper primary key? Yes, use:
# https://api.zotero.org/groups/1633743/items/ZZH5G8PB?format=tei
#
# For the conversion zotero->tei:
# https://github.com/zotero/translators/blob/master/TEI.js

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
create index if not exists bibliography_index_short_title on bibliography(short_title);
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

def fix_markup(xml):
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
	val = html.unescape(val)
	val = unicodedata.normalize("NFC", val)
	val = val.replace("&", "&amp;")
	val = "<r>%s</r>" % val
	try:
		xml = tree.parse_string(val).root
		fix_markup(xml)
		val = xml.xml()[len("<r>"):-len("</r>")]
	except expat.ExpatError:
		val = html.escape(val)
	return val

def name_first_last(rec, dflt="?"):
	first, last = rec.get("firstName"), rec.get("lastName")
	if first and last:
		return "%s %s" % (first, last)
	elif last:
		return last
	elif first:
		return "%s ?" % first
	else:
		return rec.get("name") or dflt

def name_last_first(rec, dflt="?"):
	first, last = rec.get("firstName"), rec.get("lastName")
	if last and first:
		return "%s, %s" % (last, first)
	elif last:
		return last
	elif first:
		return "?, %s" % first
	else:
		return rec.get("name") or dflt

def name_last(rec, dflt="?"):
	return rec.get("lastName") or rec.get("name") or dflt

class Writer:

	def __init__(self):
		self.buf = ""

	def space(self):
		if self.buf and not self.buf[-1].isspace():
			self.buf += " "

	def period(self): # TODO take tags into account!
		i = len(self.buf)
		while i > 0:
			i -= 1
			c = self.buf[i]
			if c == ".":
				return
			if c.isalpha() or c.isdigit():
				break
		self.buf += "."

	def text(self, s):
		self.buf += s

	def html(self, s):
		self.buf += s

	def names(self, authors):
		if not authors:
			self.text("Anonymous")
		for i, author in enumerate(authors):
			if i == 0:
				self.text(name_last_first(author))
				continue
			if i == len(authors) - 1:
				self.text(" and ")
			else:
				self.text(", ")
			self.text(name_first_last(author))
		self.period()

	def date(self, date):
		if not date:
			date = "N.\N{NBSP}d."
		self.space()
		self.text(date)
		self.period()

	def quoted(self, title):
		self.space()
		if title:
			self.text("“")
			self.text(title)
			self.period()
			self.text("”")
		else:
			self.text("Untitled")
			self.period()

	def italic(self, title):
		self.space()
		if title:
			self.html("<i>")
			self.text(title)
			self.html("</i>")
		else:
			self.text("Untitled")
		self.period()

	def series(self, rec):
		if not rec["series"]:
			return
		self.space()
		self.text(rec["series"])
		if rec["seriesNumber"]:
			self.text(" %s" % rec["seriesNumber"])
		self.period()

	def place_publisher_loc(self, rec, params):
		self.space()
		if rec["place"]:
			self.text(rec["place"])
		else:
			self.text("No place")
		publisher = rec.get("publisher")
		if publisher:
			self.text(": %s" % publisher)
		for unit, val in params["loc"]:
			abbr = cited_range_units.get(unit, unit)
			self.text(", ")
			self.text(abbr + "\N{NBSP}")
			self.text(val)
		self.period()

	def edition(self, rec):
		ed = rec["edition"]
		if not ed:
			return
		if ed == "1":
			self.text("1st ed.")
		elif ed == "2":
			self.text("2nd ed.")
		elif ed == "3":
			self.text("3rd ed.")
		elif ed.isdigit():
			self.text("%sth ed." % ed)
		else:
			self.text(ed)
			self.period()

	def url(self, rec):
		# Don't use the URL if not needed. Mostly because URL are
		# typically invalid or point to private or semi-private
		# locations (sharedocs, academia) and that we don't want to
		# deal with the mess.
		if rec["itemType"] != "report":
			return
		url = rec["url"]
		if not url:
			return
		self.space()
		self.text("URL: ")
		self.html('<a class="dh-url" href="')
		self.text(url)
		self.html('">')
		self.text(url)
		self.html('</a>')
		self.period()

cited_range_units = dict([
	("volume", "vol."),
	("appendix", "appendix"),
	("book", "book"),
	("section", "§"),
	("page", "p."),
	("item", "nº"),
	("figure", "fig."),
	("plate", "plate"),
	("table", "table"),
	("note", "n."),
	("part", "part"),
	("entry", "entry"),
	("line", "l."),
])

def render_journal_article(rec, w, params):
	w.names(rec["creators"])
	w.date(rec["date"])
	w.quoted(rec["title"])
	if rec["publicationTitle"]:
		w.space()
		w.html("<i>")
		w.text(rec["publicationTitle"])
		w.html("</i>")
		if rec["volume"]:
			w.space()
			w.text(rec["volume"])
		sep = ", "
		for unit, val in params["loc"]:
			abbr = cited_range_units.get(unit, unit)
			w.text(sep)
			w.text(abbr + "\N{NBSP}")
			w.text(val)
		w.period()
	w.url(rec)

# book
"""
  {
    "ISBN": "",
    "abstractNote": "",
    "accessDate": "",
    "archive": "",
    "archiveLocation": "",
    "callNumber": "",
    "collections": [
      "IMXEGL2I"
    ],
    "creators": [
      {
        "creatorType": "author",
        "firstName": "Benjamin Lewis",
        "lastName": "Rice"
      },
      {
        "creatorType": "author",
        "firstName": "R.",
        "lastName": "Narasimhachar"
      }
    ],
    "date": "1923",
    "dateAdded": "2023-04-25T13:03:22Z",
    "dateModified": "2023-06-29T09:09:41Z",
    "edition": "2",
    "extra": "",
    "itemType": "book",
    "key": "XVCMZSKY",
    "language": "",
    "libraryCatalog": "",
    "numPages": "",
    "numberOfVolumes": "",
    "place": "Bangalore",
    "publisher": "Mysore Government Central Press",
    "relations": {},
    "rights": "",
    "series": "Epigraphia Carnatica",
    "seriesNumber": "2",
    "shortTitle": "Rice+Narasimhachar1923",
    "tags": [],
    "title": "Inscriptions at Sravana Belgola (Revised Edition)",
    "url": "",
    "version": 199176,
    "volume": ""
  }
"""
def render_book(rec, w, params):
	w.names(rec["creators"])
	w.date(rec["date"])
	w.italic(rec["title"])
	w.edition(rec)

	w.place_publisher_loc(rec, params)
	w.url(rec)

# report
"""
  {
    "abstractNote": "",
    "accessDate": "",
    "archive": "",
    "archiveLocation": "",
    "callNumber": "",
    "collections": [
      "ZKAMV4ZC"
    ],
    "creators": [
      {
        "creatorType": "author",
        "name": "Goenawan A. Sambodo"
      }
    ],
    "date": "2018",
    "dateAdded": "2021-03-16T08:35:08Z",
    "dateModified": "2023-04-05T23:32:10Z",
    "extra": "",
    "institution": "",
    "itemType": "report",
    "key": "HCM2HCJB",
    "language": "Indonesian",
    "libraryCatalog": "",
    "pages": "",
    "place": "Yogyakarta",
    "relations": {},
    "reportNumber": "",
    "reportType": "",
    "rights": "",
    "seriesTitle": "",
    "shortTitle": "GoenawanASambodo2018_02",
    "tags": [
      {
        "tag": "GoenawanASambodo2018_02"
      }
    ],
    "title": "Kajian Singkat Prasasti Śrī Rānāpati",
    "url": "https://www.academia.edu/38202838/Kajian_singkat_prasasti_Sri_Ranapati_pdf",
    "version": 196839
  }
"""
def render_report(rec, w, params):
	w.names(rec["creators"])
	w.date(rec["date"])
	w.quoted(rec["title"])
	w.place_publisher_loc(rec, params)
	w.url(rec)

# book section
"""
{
    "ISBN": "",
    "abstractNote": "",
    "accessDate": "",
    "archive": "",
    "archiveLocation": "",
    "bookTitle": "The Buddhist Monuments in Asia",
    "callNumber": "",
    "collections": [
      "LZ2UML25"
    ],
    "creators": [
      {
        "creatorType": "author",
        "firstName": "Yoshiaki",
        "lastName": "ISHIZAWA"
      }
    ],
    "date": "1988",
    "dateAdded": "2021-05-18T07:41:32Z",
    "dateModified": "2023-06-29T05:31:44Z",
    "edition": "",
    "extra": "tex.langue: English",
    "itemType": "bookSection",
    "key": "YZ9QVXWK",
    "language": "",
    "libraryCatalog": "",
    "numberOfVolumes": "",
    "pages": "231-258",
    "place": "",
    "publisher": "Institute of Asian Ethno-Forms and Culture",
    "relations": {},
    "rights": "",
    "series": "",
    "seriesNumber": "",
    "shortTitle": "Ishizawa1988_02",
    "tags": [
      {
        "tag": "Ishizawa1988_02"
      }
    ],
    "title": "Angkor Vat",
    "url": "",
    "version": 199160,
    "volume": ""
  }
"""
def render_book_section(rec, w, params):
	w.names(rec["creators"])
	w.date(rec["date"])
	w.quoted(rec["title"])
	if rec["bookTitle"]:
		w.space()
		w.text("In: ")
		w.italic(rec["bookTitle"])
		w.edition(rec)
	if rec["volume"]:
		w.space()
		w.text("Vol.\N{NBSP}%s" % rec["volume"])
		w.period()
	w.series(rec)
	if rec["numberOfVolumes"]:
		w.space()
		w.text(rec["numberOfVolumes"])
		w.space()
		w.text("vols.")
	w.place_publisher_loc(rec, params)
	w.url(rec)

# thesis
"""
{
  "data": {
    "abstractNote": "",
    "accessDate": "",
    "archive": "",
    "archiveLocation": "",
    "callNumber": "",
    "collections": [
      "EBTHLX5L"
    ],
    "creators": [
      {
        "creatorType": "author",
        "name": "Aditia Gunawan"
      }
    ],
    "date": "2023",
    "dateAdded": "2023-06-13T09:50:20Z",
    "dateModified": "2023-06-27T22:58:46Z",
    "extra": "",
    "itemType": "thesis",
    "key": "YGEQDXT2",
    "language": "English",
    "libraryCatalog": "",
    "numPages": "",
    "place": "Paris",
    "relations": {},
    "rights": "",
    "shortTitle": "",
    "tags": [],
    "thesisType": "Doctoral Thesis",
    "title": "Sundanese Religion in the 15th Century: A Philological Study based on the Śikṣā Guru, the Sasana Mahaguru, and the Siksa Kandaṅ Karǝsian",
    "university": "École Pratique des Hautes Études, PSL University",
    "url": "",
    "version": 199074
  }
"""
def render_thesis(rec, w, params):
	w.names(rec["creators"])
	w.date(rec["date"])
	w.quoted(rec["title"])
	w.space()
	w.text(rec["thesisType"] or "Thesis")
	if rec["university"]:
		w.text(", ")
		w.text(rec["university"])
	w.period()
	w.place_publisher_loc(rec, params)
	w.url(rec)

renderers = {
	"book": render_book,
	"journalArticle": render_journal_article,
	"report": render_report,
	"bookSection": render_book_section,
	"thesis": render_thesis,
}

def fix_loc(rec, loc):
	page = rec.get("pages")
	for i, (unit, val) in enumerate(loc):
		loc[i] = (html.escape(unit), html.escape(val))
		if unit == "page":
			page = None
	if page:
		loc.insert(0, ("page", page))

def render(rec, params):
	f = renderers.get(rec["itemType"])
	if not f:
		return
	fix_loc(rec, params["loc"])
	w = Writer()
	if params["n"]:
		w.html("<b>[%s]</b>" % html.escape(params["n"]))
		w.space()
	f(rec, w, params)
	return w.buf

def make_ref_main(rec, fmt):
	if fmt == "omitname":
		return html.escape(rec["date"])
	if fmt == "ibid":
		return "<i>ibid.</i>"
	authors = rec["creators"]
	if len(authors) == 0:
		buf = "Anonymous"
	elif len(authors) == 1:
		buf = name_last(authors[0])
	elif len(authors) == 2:
		buf = "%s and %s" % (name_last(authors[0]), name_last(authors[1]))
	elif len(authors) >= 3:
		buf = "%s <i>et al.</i>" % name_last(authors[0])
	date = rec["date"] or "n.\N{NBSP}d."
	buf += " " + date
	return html.escape(buf)

def make_ref(rec, **params):
	ref = make_ref_main(rec, params["rend"])
	loc = ""
	sep = ", "
	for unit, val in params["loc"]:
		abbr = cited_range_units.get(unit, unit)
		loc += sep
		loc += html.escape(abbr + "\N{NBSP}" + val)
	return ref, loc

# TODO complain when multiple entries
def get_entry(ref, params):
	recs = db.execute("select key, json from bibliography where short_title = ?", (ref,)).fetchall()
	if not recs:
		return "", html.escape("<%s>" % ref)
	key, ret = recs[0]
	ret = render(ret["data"], params)
	return key, ret or html.escape("<%s> %s" % (ref, recs[0][1]))

# TODO complain when multiple entries
def get_ref(ref, **params):
	recs = db.execute("select key, json from bibliography where short_title = ?", (ref,)).fetchall()
	if not recs:
		return "", html.escape("<%s>" % ref), ""
	key, ret = recs[0]
	return key, *make_ref(ret["data"], **params)

if __name__ == "__main__":
	params = {"rend": "default", "loc": [], "n": ""}
	key, ref, loc = get_ref(sys.argv[1], **params)
	print(repr(ref))
