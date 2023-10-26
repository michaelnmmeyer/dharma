# When processing a text, oxygen generates zotero API calls like this:
# https://api.zotero.org/groups/1633743/items?tag=ROD1914&format=tei
# This is why tags are used, but can we generate another API call that uses a
# proper primary key? Yes, use:
# https://api.zotero.org/groups/1633743/items/ZZH5G8PB?format=tei
#
# For the conversion zotero->tei:
# https://github.com/zotero/translators/blob/master/TEI.js

# TODO: we're supposed to not have space between initials, as in T.V. instead
# of T. V. ; try to fix this when possible
# TODO try to fix trailing [;,.] in URIs
# TODO deal with roles in names (not only authors)

# TODO generate ref and entries with 1918a, 1918b, etc. when necessary

# TODO NFC + space normalization

import sys, io, json, unicodedata, html, re, time
from urllib.parse import urlparse
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

# The headers "Backoff" and "Retry-After" tell us to wait n seconds before
# issuing the next request. Not sure what's the difference between these two,
# so choose the largest value.
def next_request_delay(r):
	wait = 0
	n = r.headers.get("Backoff", "")
	if n.isdigit():
		wait = max(wait, int(n))
	n = r.headers.get("Retry-After", "")
	if n.isdigit():
		wait = max(wait, int(n))
	return wait

# See https://www.zotero.org/support/dev/web_api/v3/syncing
#
# It's not quite clear from the documentation, but there is a global "version"
# counter that is incremented whenever the database is modified. Whenever a
# record is added/modified, its "version" key is set to the current global
# version, so that it's possible to detect items that have been added/modified
# since a given version.
def zotero_items(latest_version, ret):
	s = requests.Session()
	s.headers["Zotero-API-Version"] = "3"
	s.headers["Zotero-API-Key"] = MY_API_KEY
	r = s.get(f"https://api.zotero.org/groups/{LIBRARY_ID}/items?since={latest_version}")
	cutoff = 0
	while True:
		wait = next_request_delay(r)
		if r.status_code != 200:
			if wait < 1 or wait > 20:
				# Will retry later.
				cutoff = latest_version
				break
		new_version = int(r.headers["Last-Modified-Version"])
		assert new_version >= latest_version
		if not cutoff:
			cutoff = new_version
		entries = r.json()
		assert isinstance(entries, list)
		for entry in entries:
			# Ignore all entries modified since our first request,
			# because in this case we can't rely on the pagination
			# to be correct and we might miss entries.
			if entry["version"] > cutoff:
				continue
			yield entry
		next_page = re.search(r'<([^>]+)>;\s*rel="next"', r.headers.get("Link", ""))
		if not next_page:
			break
		time.sleep(wait)
		r = s.get(next_page.group(1))
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
valid_tags = {"a", "i", "b", "sub", "sup", "span"}

def fix_markup(xml):
	for tag in xml.find(".//em"):
		tag.name = "i"
	for tag in xml.find(".//a"):
		link = tag["href"]
		if not link:
			tag.unwrap()
			continue
		tag.attrs.clear()
		tag["href"] = link
	for tag in xml.find(".//*"):
		if tag.name not in valid_tags:
			tag.unwrap()
			continue
		if tag.name != "span":
			continue
		klass = tag["class"]
		style = tag["style"]
		if klass != "nocase":
			klass = ""
		if not re.match(r"^font-variant\s*:\s*small-caps\s*;?$", style):
			style = ""
		tag.attrs.clear()
		if not klass and not style:
			tag.unwrap()
			continue
		if klass:
			tag["class"] = klass
		if style:
			tag["style"] = style

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
		return f"{first} {last}"
	elif last:
		return last
	elif first:
		return f"{first} ?"
	else:
		return rec.get("name") or dflt

def name_last_first(rec, dflt="?"):
	first, last = rec.get("firstName"), rec.get("lastName")
	if last and first:
		return f"{last}, {first}"
	elif last:
		return last
	elif first:
		return f"?, {first}"
	else:
		return rec.get("name") or dflt

def name_last(rec, dflt="?"):
	return rec.get("lastName") or rec.get("name") or dflt

#XXX normalize space

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

	def ref(self, rec):
		authors = rec["creators"]
		if len(authors) == 0:
			self.text("Anonymous")
		elif len(authors) == 1:
			self.text(name_last(authors[0]))
		elif len(authors) == 2:
			self.text("%s and %s" % (name_last(authors[0]), name_last(authors[1])))
		else:
			self.text("%s <i>et al.</i>" % name_last(authors[0]))
		self.space()
		self.date(rec, end_field=False)

	def date(self, rec, end_field=True):
		date = rec["date"]
		if not date:
			date = "N.d."
		self.space()
		self.text(date)
		if end_field:
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
			self.text("<i>")
			self.text(title)
			self.text("</i>")
		else:
			self.text("Untitled")
		self.period()

	def series(self, rec):
		if not rec["series"]:
			return
		self.space()
		self.text(rec["series"])
		if rec["seriesNumber"]:
			self.space()
			self.text(rec["seriesNumber"])
		self.period()

	def loc(self, loc):
		for unit, val in loc:
			abbr = cited_range_units.get(unit, unit)
			self.text(", ")
			self.text(abbr + "\N{NBSP}")
			self.text(val)

	def place_publisher_loc(self, rec, params):
		self.space()
		if rec["place"]:
			self.text(rec["place"])
		else:
			self.text("No place")
		publisher = rec.get("publisher")
		if publisher:
			self.text(": %s" % publisher)
		self.loc(params["loc"])
		self.period()

	def edition(self, rec):
		ed = rec["edition"]
		if not ed:
			return
		if ed == "1":
			self.text("1st edition")
		elif ed == "2":
			self.text("2nd edition")
		elif ed == "3":
			self.text("3rd edition")
		elif ed.isdigit():
			self.text("%sth edition" % ed)
		else:
			self.text(ed)
		self.period()

	def doi(self, rec):
		doi = rec.get("DOI")
		if not doi:
			return
		url = config.normalize_url(doi)
		doi = urlparse(url).path.lstrip("/")
		# All DOI start with "10.". We remove everything before that in the URI:
		# https://doi.org/10.1163/22134379-9000164 -> 10.1163/22134379-9000164
		# https://what.com/the/10.1163/22134379-9000164 -> 10.1163/22134379-9000164
		while not doi.startswith("10."):
			slash = doi.find("/")
			if slash < 0:
				return # invalid
			doi = doi[slash + 1:]
		self.text("DOI:")
		self.space()
		self.text('<a class="dh-url" href="https://doi.org/')
		self.text(doi)
		self.text('">')
		self.space()
		self.text(doi)
		self.text("</a>")
		self.period()

	def url(self, rec):
		# Don't use the URL if not needed. Mostly because URL are
		# typically invalid or point to private or semi-private
		# locations (sharedocs, academia) and that we don't want to
		# deal with the mess.
		if rec["itemType"] not in ("report", "webpage"):
			return
		urls = rec["url"].split()
		if not urls:
			return
		self.space()
		if len(urls) == 1:
			self.text("URL:")
		else:
			self.text("URLs:")
		self.space()
		for i, url in enumerate(urls):
			self.text('<a class="dh-url" href="')
			self.text(config.normalize_url(url))
			self.text('">')
			self.text(url)
			self.text('</a>')
			if i < len(urls) - 1:
				self.text("; ")
		self.period()

	def idents(self, rec):
		self.doi(rec)
		self.url(rec)

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

# journal article
"""
  {
    "DOI": "",
    "ISSN": "",
    "abstractNote": "",
    "accessDate": "",
    "archive": "",
    "archiveLocation": "",
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
    "date": "1992",
    "dateAdded": "2021-05-17T21:20:58Z",
    "dateModified": "2023-06-29T05:35:15Z",
    "extra": "tex.langue: English",
    "issue": "",
    "itemType": "journalArticle",
    "journalAbbreviation": "",
    "key": "25KCHJLX",
    "language": "English",
    "libraryCatalog": "",
    "pages": "131-137",
    "publicationTitle": "Renaissance Culturelle du Cambodge",
    "relations": {},
    "rights": "",
    "series": "",
    "seriesText": "",
    "seriesTitle": "",
    "shortTitle": "Ishizawa1992_05",
    "tags": [
      {
        "tag": "Ishizawa1992_05"
      }
    ],
    "title": "Reports on the 7th Sophia University Survey Mission for the Study and Preservation of the Angkor Monuments: 1. Policy for the Sophia University Survey Mission for the Study and Preservation of the Angkor Monuments",
    "url": "",
    "version": 199174,
    "volume": "7"
  }
"""
def render_journal_article(rec, w, params):
	w.names(rec["creators"])
	w.date(rec)
	w.quoted(rec["title"])
	if rec["publicationTitle"]:
		w.space()
		abbr = rec["journalAbbreviation"]
		name = rec["publicationTitle"]
		# Use the abbreviated journal name if possible
		if abbr:
			if name:
				name = html.escape("<i>") + name + html.escape("</i>")
				w.text(f'<abbr data-tip="{name}"><i>{abbr}</i></abbr>')
			else:
				w.text(f'<i>{abbr}</i>')
		else:
			w.text(f'<i>{name}</i>')
		if rec["volume"]:
			w.space()
			w.text(rec["volume"])
		if rec["issue"]:
			w.space()
			w.text("(%s)" % rec["issue"])
		w.loc(params["loc"])
		w.period()
	w.idents(rec)

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
	w.date(rec)
	w.italic(rec["title"])
	w.edition(rec)
	w.place_publisher_loc(rec, params)
	w.idents(rec)

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
	w.idents(rec)

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
	w.date(rec)
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
	w.idents(rec)

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
	w.date(rec)
	w.quoted(rec["title"])
	w.space()
	w.text(rec["thesisType"] or "Thesis")
	if rec["university"]:
		w.text(", ")
		w.text(rec["university"])
	w.period()
	w.place_publisher_loc(rec, params)
	w.idents(rec)

# web pages
"""
  {
    "abstractNote": "",
    "accessDate": "",
    "collections": [],
    "creators": [
      {
        "creatorType": "author",
        "firstName": "Philip N",
        "lastName": "Jenner"
      }
    ],
    "date": "n.d.",
    "dateAdded": "2023-10-20T07:50:06Z",
    "dateModified": "2023-10-20T08:04:25Z",
    "extra": "",
    "itemType": "webpage",
    "key": "Y6HD9LEE",
    "language": "English",
    "relations": {},
    "rights": "",
    "shortTitle": "",
    "tags": [],
    "title": "Analysis: pre-Angkor, Angkor and Middle Khmer Inscriptions",
    "url": "http://sealang.net/oldkhmer/text.htm",
    "version": 203590,
    "websiteTitle": "",
    "websiteType": ""
  }
"""
def render_webpage(rec, w, params):
	w.names(rec["creators"])
	w.date(rec)
	w.quoted(rec["title"])
	w.idents(rec)

renderers = {
	"book": render_book,
	"journalArticle": render_journal_article,
	"report": render_report,
	"bookSection": render_book_section,
	"thesis": render_thesis,
	"webpage": render_webpage,
}

def fix_loc(rec, loc):
	page = rec.get("pages")
	for i, (unit, val) in enumerate(loc):
		loc[i] = (html.escape(unit), html.escape(val))
		if unit == "page":
			page = None
	if page:
		# Always use "-"
		page = page.replace("\N{en dash}", "-")
		loc.insert(0, ("page", page))

def render(rec, params):
	f = renderers.get(rec["itemType"])
	if not f:
		return
	fix_loc(rec, params["loc"])
	w = Writer()
	if params["n"]:
		w.text("<b>[%s]</b>" % html.escape(params["n"]))
		w.space()
	f(rec, w, params)
	return w.buf

def make_ref(rec, **params):
	w = Writer()
	fmt = params["rend"]
	if fmt == "omitname":
		w.date(rec, end_field=False)
	elif fmt == "ibid":
		w.text("<i>ibid.</i>")
	elif fmt == "default":
		w.ref(rec)
	else:
		assert 0
	fix_loc(rec, params["loc"])
	w.loc(params["loc"])
	return w.buf, ""

def fix_record(rec):
	date = rec.get("date")
	if date:
		# Always use "-"
		date = date.replace("\N{en dash}", "-")
		# The ZG prescribes to use n.d."
		if re.match(r"^n\.\s?d\.?$", date, re.I):
			date = None
		rec["date"] = date
	publisher = rec.get("publisher")
	if publisher:
		# The ZG prescribes to use "n.pub" when there is no publisher
		if re.match(r"^n\.\s?pub\.?$", publisher, re.I):
			publisher = None
		rec["publisher"] = publisher

# TODO complain when multiple entries
def get_entry(ref, **params):
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
	key, entry = get_entry(sys.argv[1], **params)
	print(repr(entry))
