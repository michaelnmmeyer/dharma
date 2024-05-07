# For the conversion zotero->tei, this code is used:
# https://github.com/zotero/translators/blob/master/TEI.js
# The documentation for entry types and fields is at:
# https://www.zotero.org/support/kb/item_types_and_fields

import logging, unicodedata, html, re, time
from urllib.parse import urlparse
import requests # pip install requests
from dharma import common, tree

LIBRARY_ID = 1633743
MY_API_KEY = "ojTBU4SxEQ4L0OqUhFVyImjq"

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
def zotero_modified(latest_version, ret):
	s = requests.Session()
	s.headers["Zotero-API-Version"] = "3"
	s.headers["Zotero-API-Key"] = MY_API_KEY
	# The "since" param is not inclusive, this returns items whose version
	# is > latest_version.
	url = f"https://api.zotero.org/groups/{LIBRARY_ID}/items?since={latest_version}"
	logging.info(url)
	r = s.get(url)
	cutoff = 0
	while True:
		wait = next_request_delay(r)
		if r.status_code != 200:
			if wait < 1 or wait > 20:
				# Will retry later.
				logging.info(f"query failed with {r.status_code}, headers: {r.headers}")
				logging.info(f"resetting biblio to {latest_version}")
				cutoff = latest_version
				break
		new_version = int(r.headers["Last-Modified-Version"])
		assert new_version >= latest_version
		if not cutoff:
			cutoff = new_version
			logging.info(f"zotero new version: {cutoff}")
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
		url = next_page.group(1)
		logging.info(url)
		r = s.get(url)
	ret.append(cutoff)

def zotero_deleted(latest_version):
	s = requests.Session()
	s.headers["Zotero-API-Version"] = "3"
	s.headers["Zotero-API-Key"] = MY_API_KEY
	# Only a single page for this request.
	url = f"https://api.zotero.org/groups/{LIBRARY_ID}/deleted?since={latest_version}"
	logging.info(url)
	r = s.get(url)
	r.raise_for_status()
	return r.json().get("items", [])

@common.transaction("texts")
def update():
	db = common.db("texts")
	(min_version,) = db.execute("select value from metadata where key = 'biblio_latest_version'").fetchone()
	ret = []
	for entry in zotero_modified(min_version, ret):
		db.execute("""insert or replace
			into biblio_data(key, version, json, sort_key)
			values(?, ?, ?, ?)""",
			(entry["key"], entry["version"], entry, sort_key(entry["data"])))
	assert len(ret) == 1
	max_version = ret.pop()
	for key in zotero_deleted(min_version):
		db.execute("delete from biblio_data where key = ? and version <= ?", (key, max_version))
	db.execute("update metadata set value = ? where key = 'biblio_latest_version'", (max_version,))
	# For now, use brute force for generating sort keys. But we only need
	# to do that when the code that generates the sort key changes.
	for key, rec in db.execute("select key, json -> '$.data' from biblio_data"):
		rec = common.from_json(rec)
		db.execute("update biblio_data set sort_key = ? where key = ?", (sort_key(rec), key))
	db.execute("replace into metadata values('last_updated', strftime('%s', 'now'))")

anonymous = "No name"

def multiple_pages(s):
	return any(c in s for c in ",-\N{en dash}\N{em dash}")

class Writer:

	def __init__(self):
		self.xml = tree.parse_string('<p class="bib-entry"/>').root

	def output(self):
		for X in self.xml.find(".//X"):
			X.unwrap()
		return self.xml.xml()

	def space(self):
		text = self.xml.text(space="preserve")
		if text and not text[-1].isspace():
			self.add(" ")

	def period(self):
		text = self.xml.text()
		j = len(text)
		while j > 0:
			j -= 1
			c = text[j]
			if c in ".?!":
				return
			if c.isalpha() or c.isdigit():
				break
		self.add(".")

	def add(self, s):
		if isinstance(s, tree.Node):
			s = s.copy()
		self.xml.append(s)

	# John Doe
	def name_first_last(self, rec):
		first, last = rec.get("firstName"), rec.get("lastName")
		if first and last:
			self.add(first)
			self.space()
			self.add(last)
		elif last:
			self.add(last)
		elif first:
			self.add(first)
			self.space()
			self.add(anonymous)
		else:
			self.add(rec.get("name") or anonymous)

	# Doe, John
	def name_last_first(self, rec):
		first, last = rec.get("firstName"), rec.get("lastName")
		if last and first:
			self.add(last)
			self.add(", ")
			self.add(first)
		elif last:
			self.add(last)
		elif first:
			self.add(anonymous)
			self.add(", ")
			self.add(first)
		else:
			self.add(rec.get("name") or anonymous)

	# Doe
	def name_last(self, rec):
		self.add(rec.get("lastName") or rec.get("name") or anonymous)

	def front_creators(self, rec, skip_editors=False):
		authors = []
		for creator in rec["creators"]:
			if creator["creatorType"] in ("bookAuthor", "editor"):
				if skip_editors:
					continue
			elif creator["creatorType"] != "author":
				continue
			authors.append(creator)
		if not authors:
			self.add(anonymous)
		for i, author in enumerate(authors):
			if i == 0:
				self.name_last_first(author)
				continue
			if i == len(authors) - 1:
				self.add(" and ")
			else:
				self.add(", ")
			self.name_first_last(author)
		self.period()

	def by_editors(self, rec):
		self.back_creators(rec, use_authors=False, use_editors=True)

	def by_authors(self, rec):
		self.back_creators(rec, use_authors=True, use_editors=False)

	def by_all_authors(self, rec):
		self.back_creators(rec, use_authors=True, use_editors=True)

	def back_creators(self, rec, use_authors=False, use_editors=True):
		editors = []
		authors = []
		for creator in rec["creators"]:
			if use_authors:
				if creator["creatorType"] == "author":
					authors.append(creator)
			if use_editors:
				if creator["creatorType"] == "editor":
					editors.append(creator)
				elif creator["creatorType"] == "bookAuthor":
					authors.append(creator)
		for creators, s in [(authors, "By"), (editors, "Edited by")]:
			if not creators:
				continue
			self.space()
			self.add(s)
			self.space()
			for i, creator in enumerate(creators):
				if i == 0:
					self.name_first_last(creator)
					continue
				if i == len(creators) - 1:
					self.add(" and ")
				else:
					self.add(", ")
				self.name_first_last(creator)
			self.period()

	def shorthand(self, rec):
		self.add(rec["_shorthand"])
		self.period()

	def entry_front(self, rec, skip_editors=False):
		if rec["_shorthand"]:
			self.shorthand(rec)
		else:
			self.front_creators(rec, skip_editors)
			self.date(rec)

	def ref(self, rec):
		authors = []
		for creator in rec["creators"]:
			if rec["itemType"] == "bookSection" and creator["creatorType"] in ("editor", "bookAuthor"):
				continue
			authors.append(creator)
		if len(authors) == 0:
			self.add(anonymous)
		elif len(authors) == 1:
			self.name_last(authors[0])
		elif len(authors) == 2:
			self.name_last(authors[0])
			self.space()
			self.add("and")
			self.space()
			self.name_last(authors[1])
		else:
			self.name_last(authors[0])
			self.space()
			tag = tree.Tag("i")
			tag.append("et al.")
			self.add(tag)
		self.space()
		self.date(rec, end_field=False)

	def date(self, rec, end_field=True, space=True):
		date = rec["date"]
		if not date:
			date = "N.d."
		if space:
			self.space()
		self.add(date)
		if end_field:
			self.period()

	# Quoted title (for articles, etc.)
	def quoted(self, title):
		self.space()
		if title:
			self.add("“")
			self.add(title)
			self.period()
			self.add("”")
		else:
			self.add("Untitled")
			self.period()

	# Title in italics (for books, etc.)
	def italics(self, title):
		self.space()
		if title:
			tag = tree.Tag("i")
			tag.append(title)
			self.add(tag)
		else:
			self.add("Untitled")
		self.period()

	def volume_and_series(self, rec):
		vol = rec.get("volume")
		if vol:
			self.space()
			self.add("Vol.\N{nbsp}")
			self.add(vol)
			self.period()
		# seriesText and seriesTitle are apparently deprecated.
		series = rec.get("series")
		if series:
			self.space()
			self.add(series)
			n = rec.get("seriesNumber")
			if n:
				self.space()
				self.add(n)
			self.period()
		n = rec.get("numberOfVolumes")
		if n:
			self.space()
			self.add(n)
			self.space()
			self.add("vols.")

	def entry_loc(self, loc):
		if not loc:
			return
		first = True
		sep = " "
		for unit, val in loc:
			self.add(sep)
			sep = ", "
			assert unit in cited_range_units
			if unit != "mixed":
				if unit == "page":
					# TODO maybe not only for pages?
					val = val.replace("-", "\N{en dash}")
				# TODO not possible to tell unambiguously whether we have several units or not
				if multiple_pages(val):
					unit = common.numberize(unit, 2)
				else:
					unit = common.numberize(unit, 1)
				if first:
					unit = common.sentence_case(unit)
					first = False
				self.add(unit)
				self.space()
			if first:
				val = common.sentence_case(val)
				first = False
			self.add(val)
		self.period()

	def loc(self, loc):
		if not loc:
			return
		sep = " "
		for unit, val in loc:
			self.add(sep)
			sep = ", "
			assert unit in cited_range_units
			if unit != "mixed":
				if unit == "page":
					# TODO maybe not only for pages?
					val = val.replace("-", "\N{en dash}")
				abbr_sg, abbr_pl = cited_range_units[unit]
				# TODO not possible to tell unambiguously whether we have several units or not
				if multiple_pages(val):
					unit = abbr_pl
				else:
					unit = abbr_sg
				self.add(unit)
				self.add("\N{nbsp}")
			self.add(val)

	def pages(self, rec):
		s = rec.get("pages")
		if not s:
			return
		self.add(", ")
		if multiple_pages(s):
			self.add("pp.\N{nbsp}")
		else:
			self.add("p.\N{nbsp}")
		s = s.replace("-", "\N{en dash}")
		self.add(s)

	def place_publisher_loc(self, rec):
		self.space()
		if (place := rec.get("place")):
			self.add(place)
		else:
			self.add("No place")
		if (publisher := rec.get("publisher")):
			self.add(": ")
			self.add(publisher)
		if rec.get("_shorthand") and rec["date"]:
			self.add(", ")
			self.date(rec, end_field=False)
		self.pages(rec)
		self.period()

	def edition(self, rec):
		ed = rec["edition"]
		if not ed:
			return
		self.space()
		txt = ed.text()
		if txt == "1":
			self.add("1st edition")
		elif txt == "2":
			self.add("2nd edition")
		elif txt == "3":
			self.add("3rd edition")
		elif txt.isdigit():
			self.add(f"{txt}th edition")
		else:
			self.add(ed)
		self.period()

	def doi(self, rec):
		doi = rec.get("DOI")
		if not doi:
			return
		url = common.normalize_url(doi)
		doi = urlparse(url).path.lstrip("/")
		# All DOI start with "10.". We remove everything before that in the URI:
		# https://doi.org/10.1163/22134379-9000164 -> 10.1163/22134379-9000164
		# https://what.com/the/10.1163/22134379-9000164 -> 10.1163/22134379-9000164
		while not doi.startswith("10."):
			slash = doi.find("/")
			if slash < 0:
				return # invalid
			doi = doi[slash + 1:]
		self.space()
		self.add("DOI:")
		self.space()
		tag = tree.Tag("a", {"class": "url", "href": f"https://doi.org/{doi}"})
		tag.append(doi)
		self.add(tag)
		self.period()

	def url_visible(self, urls):
		self.space()
		if len(urls) == 1:
			self.add("URL:")
		else:
			self.add("URLs:")
		self.space()
		for i, url in enumerate(urls):
			tag = tree.Tag("a", {"class": "url", "href": url})
			tag.append(url)
			self.add(tag)
			if i < len(urls) - 1:
				self.add("; ")
		self.period()

	def url_hidden(self, urls):
		for url in urls:
			tag = tree.Tag("a", {"href": url})
			tag.append("[URL]")
			self.space()
			self.add(tag)
		self.period()

	def url(self, rec):
		urls = [common.normalize_url(url.rstrip(";"))
			for url in rec["url"].split()]
		if not urls:
			return
		# I would rather show the full URL if needed to identify the
		# record, in case people want to print it.
		if rec["itemType"] in ("report", "webpage") and False:
			self.url_visible(urls)
		else:
			self.url_hidden(urls)

	def idents(self, rec):
		self.doi(rec)
		self.url(rec)

cited_range_units = {
	"volume": ("vol.", "vols."),
	"appendix": ("appendix", "appendices"),
	"book": ("book", "books"),
	"section": ("§", "§§"),
	"page": ("p.", "pp."),
	"item": ("№", "№"),
	"figure": ("fig.", "figs."),
	"plate": ("plate", "plates"),
	"table": ("table", "tables"),
	"note": ("n.", "nn."),
	"part": ("part", "parts"),
	"entry": ("s.v.", "s.vv.",),
	"line": ("l.", "ll."),
	"mixed": None,
}

creator_types = ["author", "editor", "bookAuthor"]

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
	w.entry_front(rec)
	w.quoted(rec["title"])
	if rec["_shorthand"]:
		w.by_authors(rec)
	if rec["publicationTitle"]:
		w.space()
		abbr = rec["journalAbbreviation"]
		name = rec["publicationTitle"]
		# Use the abbreviated journal name if possible.
		if abbr and name:
			name.name = "i"
			tag = tree.Tag("abbr", {"data-tip": name.xml()})
			tagi = tree.Tag("i")
			tagi.append(abbr)
			tag.append(tagi)
			w.add(tag)
		elif abbr:
			tag = tree.Tag("i")
			tag.append(abbr)
			w.add(tag)
		elif name:
			tag = tree.Tag("i")
			tag.append(name)
			w.add(tag)
		if rec["volume"]:
			w.space()
			w.add(rec["volume"])
		if rec["issue"]:
			w.space()
			w.add("(")
			w.add(rec["issue"])
			w.add(")")
		if rec["_shorthand"] and rec["date"]:
			w.space()
			w.add("(")
			w.date(rec, end_field=False, space=False)
			w.add(")")
		w.pages(rec)
		w.period()
	w.idents(rec)
	w.entry_loc(params.get("loc"))

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
	w.entry_front(rec)
	w.italics(rec["title"])
	if rec["_shorthand"]:
		w.by_all_authors(rec)
	w.edition(rec)
	w.volume_and_series(rec)
	w.place_publisher_loc(rec)
	w.idents(rec)
	w.entry_loc(params.get("loc"))

# conference paper
"""
  {
    "DOI": "",
    "ISBN": "",
    "abstractNote": "",
    "accessDate": "",
    "archive": "",
    "archiveLocation": "",
    "callNumber": "",
    "collections": [
      "D7CGVND8",
      "ZKAMV4ZC"
    ],
    "conferenceName": "Seminar Sejarah Nasional II, August 26th-29th 1970, Yogyakarta",
    "creators": [
      {
        "creatorType": "author",
        "firstName": "M. M.",
        "lastName": "Sukarto K. Atmodjo"
      }
    ],
    "date": "1970",
    "dateAdded": "2019-10-29T11:56:33Z",
    "dateModified": "2023-09-08T03:48:04Z",
    "extra": "",
    "itemType": "conferencePaper",
    "key": "3ZE7ICXR",
    "language": "Indonesian",
    "libraryCatalog": "",
    "pages": "52",
    "place": "Yogyakarta",
    "proceedingsTitle": "",
    "publisher": "",
    "relations": {
      "dc:replaces": "http://zotero.org/groups/1633743/items/PNXXJIQ6"
    },
    "rights": "",
    "series": "",
    "shortTitle": "SukartoKAtmodjo1970_01",
    "tags": [
      {
        "tag": "SukartoAtmodjo1970_02"
      }
    ],
    "title": "Prasasti Buyan-Sanding-Tamblingan dari djaman Radja Jayapangus",
    "url": "",
    "version": 201774,
    "volume": ""
  }
"""
def render_conference_paper(rec, w, params):
	w.entry_front(rec, skip_editors=True)
	w.quoted(rec["title"])
	if rec["_shorthand"]:
		w.by_authors(rec)
	if rec["proceedingsTitle"]:
		w.space()
		w.add("In: ")
		w.italics(rec["proceedingsTitle"])
	w.by_editors(rec)
	w.volume_and_series(rec)
	w.place_publisher_loc(rec)
	w.idents(rec)
	w.entry_loc(params.get("loc"))

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
	w.entry_front(rec)
	w.quoted(rec["title"])
	if rec["_shorthand"]:
		w.by_authors(rec)
	w.place_publisher_loc(rec)
	w.idents(rec)
	w.entry_loc(params.get("loc"))

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
	w.entry_front(rec, skip_editors=True)
	w.quoted(rec["title"])
	if rec["_shorthand"]:
		w.by_authors(rec)
	if rec["bookTitle"]:
		w.space()
		w.add("In: ")
		w.italics(rec["bookTitle"])
		w.edition(rec)
	w.by_editors(rec)
	w.volume_and_series(rec)
	w.place_publisher_loc(rec)
	w.idents(rec)
	w.entry_loc(params.get("loc"))

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
	w.entry_front(rec)
	w.quoted(rec["title"])
	if rec["_shorthand"]:
		w.by_authors(rec)
	w.space()
	w.add(rec["thesisType"] or "Thesis")
	if rec["university"]:
		w.add(", ")
		w.add(rec["university"])
	w.period()
	w.place_publisher_loc(rec)
	w.idents(rec)
	w.entry_loc(params.get("loc"))

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
	w.entry_front(rec)
	w.quoted(rec["title"])
	if rec["_shorthand"]:
		w.by_authors(rec)
	if rec["_shorthand"] and rec["date"]:
		w.date(rec)
	w.idents(rec)
	w.entry_loc(params.get("loc"))

""""
  {
  "data": {
    "ISSN": "",
    "abstractNote": "",
    "accessDate": "",
    "archive": "",
    "archiveLocation": "",
    "callNumber": "",
    "collections": [],
    "creators": [],
    "date": "1991-11-13",
    "dateAdded": "2022-10-03T17:32:26Z",
    "dateModified": "2022-10-04T06:52:21Z",
    "edition": "Pondicherry",
    "extra": "",
    "itemType": "newspaperArticle",
    "key": "2Y5D2W4J",
    "language": "Tamil",
    "libraryCatalog": "",
    "pages": "",
    "place": "",
    "publicationTitle": "Dinamalar",
    "relations": {},
    "rights": "",
    "section": "",
    "shortTitle": "Dinamalar1991_01",
    "tags": [
      {
        "tag": "Dinamalar1991_01"
      }
    ],
    "title": "[Discovery of inscribed stele at Arasalapuram]",
    "url": "",
    "version": 188223
  }
"""
def render_newspaper_article(rec, w, params):
	w.entry_front(rec)
	w.quoted(rec["title"])
	if rec["_shorthand"]:
		w.by_authors(rec)
	w.italics(rec["publicationTitle"])
	w.edition(rec)
	w.place_publisher_loc(rec)
	w.idents(rec)
	w.entry_loc(params.get("loc"))

"""
{
    "DOI": "10.5281/zenodo.2574901",
    "abstractNote": "",
    "accessDate": "",
    "archive": "",
    "archiveLocation": "",
    "callNumber": "",
    "citationKey": "",
    "collections": [],
    "creators": [
      {
        "creatorType": "author",
        "firstName": "Dániel",
        "lastName": "Balogh"
      },
      {
        "creatorType": "author",
        "firstName": "Csaba",
        "lastName": "Kiss"
      },
      {
        "creatorType": "author",
        "firstName": "Eszter",
        "lastName": "Somogyi"
      }
    ],
    "date": "2019",
    "dateAdded": "2021-08-26T08:41:38Z",
    "dateModified": "2021-08-26T09:11:14Z",
    "extra": "",
    "format": "",
    "identifier": "",
    "itemType": "dataset",
    "key": "JPVZFKHW",
    "language": "",
    "libraryCatalog": "",
    "relations": {},
    "repository": "Zenodo",
    "repositoryLocation": "",
    "rights": "",
    "shortTitle": "Balogh+al2019_01",
    "tags": [
      {
        "tag": "Balogh+al2019_01"
      }
    ],
    "title": "Siddham Epigraphic Archive - Texts in EpiDoc [Data set]",
    "type": "",
    "url": "https://doi.org/10.5281/zenodo.2574901",
    "version": 197208,
    "versionNumber": "7"
}
"""
def render_dataset(rec, w, params):
	w.entry_front(rec)
	w.quoted(rec["title"])
	if rec["_shorthand"]:
		w.by_authors(rec)
	if rec["repository"]:
		w.space()
		w.add(rec["repository"])
		w.period()
	if rec["_shorthand"] and rec["date"]:
		w.date(rec)
	w.idents(rec)
	w.entry_loc(params.get("loc"))

renderers = {
	"book": render_book,
	"journalArticle": render_journal_article,
	"conferencePaper": render_conference_paper,
	"report": render_report,
	"bookSection": render_book_section,
	"thesis": render_thesis,
	"webpage": render_webpage,
	"newspaperArticle": render_newspaper_article,
	"dataset": render_dataset,
}

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
		if tag.name not in valid_tags and isinstance(tag.parent, tree.Tag):
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

def text_nodes(xml):
	for node in xml:
		match node:
			case tree.String():
				yield node
			case tree.Tag():
				yield from text_nodes(node)

def normalize_space(xml):
	nodes = list(text_nodes(xml))
	i = 0
	for i, node in enumerate(nodes):
		s = re.sub(r"\s+", " ", str(node))
		if i == 0:
			s = s.lstrip()
		if i == len(nodes) - 1:
			s = s.rstrip()
		if i < len(nodes) - 1 and s and s[-1].isspace() and nodes[i + 1] and nodes[i + 1][0].isspace():
			s = s.rstrip()
		node.replace_with(s)

# TODO:
# add interface for correcting entries
# we're supposed to not have space between initials, as in T.V. instead
# of T. V. ; try to fix this when possible
# try to fix trailing [;,.] in URIs
def fix_value(s):
	s = html.unescape(s)
	s = unicodedata.normalize("NFC", s)
	# XXX tell people not to use HTML entities.
	# XXX shouldn't replace &lt; and &gt;
	s = s.replace("&", "&amp;")
	try:
		s = tree.parse_string("<X>%s</X>" % s)
	except tree.Error:
		# Don't try to fix this.
		s = tree.parse_string("<X>%s</X>" % html.escape(s))
	fix_markup(s)
	normalize_space(s)
	if not s.text():
		return ""
	return s.root

def fix_rec(rec):
	# TODO normalize_space()
	date = rec.get("date")
	if date:
		# Always use "-"
		date = date.replace("\N{en dash}", "-")
		# The ZG prescribes to use n.d."
		if re.match(r"^n\.\s?d\.?$", date, re.I):
			date = ""
		rec["date"] = date
	page = rec.get("pages")
	if page:
		# Always use "-"
		page = page.replace("\N{en dash}", "-")
		rec["pages"] = page
	publisher = rec.get("publisher")
	if publisher:
		# The ZG prescribes to use "n.pub" when there is no publisher
		if re.match(r"^n\.\s?pub\.?$", publisher, re.I):
			publisher = ""
		rec["publisher"] = publisher
	for line in rec.get("extra", "").splitlines():
		chunks = [common.normalize_space(c)
			for c in re.split(r"[=:]", line, maxsplit=1)]
		if len(chunks) != 2:
			continue
		key, value = chunks
		if key.lower() == "shorthand":
			rec["_shorthand"] = value
	rec.setdefault("_shorthand", "")
	for key, value in rec.copy().items():
		# TODO should only allow html in specific fields (title?)
		# because gets messy
		if key in ("key", "filename", "itemType", "pages", "url", "DOI", "callNumber", "extra", "_shorthand", "date"): # XXX figure out other "id" fields
			continue
		if isinstance(value, str):
			rec[key] = fix_value(value)
	# The zotero people changed str to list in recent entries.
	for creator in rec["creators"]:
		for field in ("firstName", "lastName", "name"):
			val = creator.get(field)
			if not val:
				continue
			if isinstance(val, list):
				val = " ".join(val)
			creator[field] = val

# TODO generate ref and entries with 1918a, 1918b, etc. when necessary; in the global biblio or in the local one? and is this really needed?

PER_PAGE = 100

class Entry:

	def __init__(self, short_title):
		self.short_title = short_title
		self._data = None
		self.records_nr = -1
		self._page = None

	@staticmethod
	def wrap(data):
		self = Entry(data["shortTitle"])
		self._data = data
		fix_rec(self._data)
		self.records_nr = 1
		return self

	def __str__(self):
		return self._try_format_entry()

	def _try_format_entry(self, loc=[], n=None):
		data = self.data
		if not data:
			if self.records_nr == 0:
				return self._invalid_entry("Not found in bibliography")
			return self._invalid_entry("Multiple bibliographic entries bear this short title")
		f = renderers.get(data["itemType"])
		if not f:
			return self._invalid_entry(f"Entry type {data['itemType']!r} not supported")
		return self._format_entry(f, data, loc, n)

	@property
	def key(self):
		data = self.data
		if not data:
			return
		return data["key"]

	@property
	def valid(self):
		return bool(self.data)

	def _format_entry(self, f, rec, loc, n):
		w = Writer()
		w.xml["id"] = f"bib-key-{self.key}"
		if n:
			tag = tree.Tag("b")
			tag.append("[")
			tag.append(n)
			tag.append("]")
			w.add(tag)
			w.space()
		f(rec, w, {"loc": loc, "n": n})
		w.space()
		tag = tree.Tag("i", {
			"class": "fas fa-edit",
			"style": "display:inline;",
			"data-tip": "Edit on zotero.org",
		})
		tag.append(" ")
		lnk = tree.Tag("a", href=f"https://www.zotero.org/groups/1633743/erc-dharma/items/{self.key}")
		lnk.append(tag)
		w.add(lnk)
		return w.output()

	def _invalid_entry(self, reason):
		r = tree.Tag("p", **{"class": "bib-entry"})
		if self.key:
			r["id"] = f"bib-key-{self.key}"
		span = tree.Tag("span", **{"class": "bib-ref-invalid"})
		span["data-tip"] = reason
		span.append(self.short_title)
		r.append(span)
		return r.xml()

	@property
	def data(self):
		if self.records_nr >= 0:
			return self._data
		recs = common.db("texts").execute("""
			select json ->> '$.data'
			from biblio_data where short_title = ?""",
			(self.short_title,)).fetchall()
		self.records_nr = len(recs)
		if self.records_nr == 1:
			self._data = common.from_json(recs[0][0])
			fix_rec(self._data)
		else:
			self._page = -1
		return self._data

	@property
	def page(self):
		if self._page is not None:
			return self._page
		db = common.db("texts")
		(index,) = db.execute("""
			select pos - 1
			from (select row_number()
				over(order by sort_key) as pos,
				key from biblio_data where sort_key is not null)
			where key = ?""", (self.key,)).fetchone()
		self._page = (index + PER_PAGE - 1) // PER_PAGE
		return self._page

	def reference(self, rend="default", loc=[], external_link=True, siglum=None):
		return Reference(self, rend, loc, external_link, siglum)

	def contents(self, loc=[], n=None):
		if not loc and not n:
			return self
		return Contents(self, loc, n)

class Contents:

	def __init__(self, entry, loc, n):
		self.entry = entry
		self.loc = loc
		self.n = n

	def __str__(self):
		return self.entry._try_format_entry(self.loc, self.n)

class Reference:

	def __init__(self, entry, rend, loc, external_link, siglum):
		self.entry = entry
		self.rend = rend
		self.loc = loc
		self.external_link = external_link
		self.siglum = siglum

	def _invalid_ref(self, reason):
		r = tree.Tag("a", {
			"class": "nav-link bib-ref-invalid",
			"data-tip": reason,
		})
		r.append(self.entry.short_title)
		return r.xml()

	def __str__(self):
		rec = self.entry.data
		assert not self.entry.records_nr < 0
		if self.entry.records_nr != 1:
			if self.entry.records_nr == 0:
				return self._invalid_ref("Not found in bibliography")
			return self._invalid_ref("Multiple bibliographic entries bear this short title")
		return self._make_reference(rec)

	def _make_reference(self, rec):
		w = Writer()
		w.xml.name = "span"
		w.xml.attrs.clear()
		tag = tree.Tag("a", {"class": "bib-ref"})
		if self.external_link:
			tag["href"] = f"/bibliography/page/{self.entry.page}#bib-key-{self.entry.key}"
		else:
			tag["href"] = f"#bib-key-{self.entry.key}"
		w.xml.append(tag)
		w.xml = tag
		if self.siglum:
			tag = tree.Tag("span")
			w.xml.append(tag)
			w.xml = tag
			w.ref(rec)
			w.xml = w.xml.parent
			w.xml["data-tip"] = tag.xml()
			tag.delete()
			w.add(self.siglum)
		else:
			if self.rend == "omitname":
				shorthand = rec.get("_shorthand")
				if shorthand:
					w.add(shorthand)
				else:
					w.date(rec, end_field=False)
			elif self.rend == "ibid":
				tag = tree.Tag("i")
				tag.append("ibid.")
				w.add(tag)
			elif self.rend == "default":
				shorthand = rec.get("_shorthand")
				if shorthand:
					w.add(shorthand)
				else:
					w.ref(rec)
			else:
				assert 0
		w.xml = w.xml.parent
		if self.loc:
			w.add(",")
			w.loc(self.loc)
		return w.output()

def sort_key(rec):
	rec = rec.copy()
	typ = rec["itemType"]
	if typ not in renderers:
		return
	skip_editors = typ == "bookSection"
	fix_rec(rec)
	key = ""
	if (shorthand := rec.get("_shorthand")):
		key = shorthand
	else:
		# Only pick the first creator.
		for creator in rec["creators"]:
			if skip_editors and creator["creatorType"] in ("editor", "bookAuthor"):
				continue
			author = creator.get("lastName") or creator.get("name", "")
			key = author + " " + rec["date"]
			break
	key += " " + rec["key"]
	return key

if __name__ == "__main__":
	@common.transaction("texts")
	def main():
		db = common.db("texts")
		for (doc,) in db.execute("""select json ->> '$.data' from biblio_data
			where sort_key is not null
		"""):
			doc = common.from_json(doc)
			print(doc, sort_key(doc))
	main()
