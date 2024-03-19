# When processing a text, oxygen generates zotero API calls like this:
# https://api.zotero.org/groups/1633743/items?tag=ROD1914&format=tei
#
# This is why tags are used, but we can generate API call that us
# the actual primary key:
# https://api.zotero.org/groups/1633743/items/ZZH5G8PB?format=tei
#
# For the conversion zotero->tei:
# https://github.com/zotero/translators/blob/master/TEI.js

import sys, logging, io, json, unicodedata, html, re, time
from urllib.parse import urlparse
import requests
from dharma import config, tree

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
def zotero_items(latest_version, ret):
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

@config.transaction("texts")
def update():
	db = config.db("texts")
	db.execute("begin")
	(max_version,) = db.execute("select value from metadata where key = 'biblio_latest_version'").fetchone()
	ret = []
	for entry in zotero_items(max_version, ret):
		db.execute("""insert or replace into biblio_data(key, version, json, sort_key)
			values(?, ?, ?, ?)""", (entry["key"], entry["version"], entry, sort_key(entry["data"])))
	assert len(ret) == 1
	db.execute("update metadata set value = ? where key = 'biblio_latest_version'", tuple(ret))
	db.execute("commit")

anonymous = "No name"

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
		self.xml.append(s)

	def tag(self, name, *args, **kwargs):
		self.xml.coalesce()
		return self.xml.tree.tag(name, *args, **kwargs)

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

	def name_last(self, rec):
		self.add(rec.get("lastName") or rec.get("name") or anonymous)

	def authors(self, rec, skip_editors=False):
		authors = []
		for creator in rec["creators"]:
			if skip_editors and creator["creatorType"] == "editor":
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

	def edited_by(self, rec):
		editors = []
		for creator in rec["creators"]:
			if creator["creatorType"] == "editor":
				editors.append(creator)
		if not editors:
			return
		self.space()
		self.add("Edited by")
		self.space()
		for i, editor in enumerate(editors):
			if i == 0:
				self.name_first_last(editor)
				continue
			if i == len(editors) - 1:
				self.add(" and ")
			else:
				self.add(", ")
			self.name_first_last(editor)
		self.period()

	def ref(self, rec):
		authors = rec["creators"]
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
			tag = self.tag("i")
			tag.append("et al.")
			self.add(tag)
		self.space()
		self.date(rec, end_field=False)

	def date(self, rec, end_field=True):
		date = rec["date"]
		if not date:
			date = "N.d."
		self.space()
		self.add(date)
		if end_field:
			self.period()

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

	def italic(self, title):
		self.space()
		if title:
			tag = self.tag("i")
			tag.append(title)
			self.add(tag)
		else:
			self.add("Untitled")
		self.period()

	def series(self, rec):
		if not rec["series"]:
			return
		self.space()
		self.add(rec["series"])
		if rec["seriesNumber"]:
			self.space()
			self.add(rec["seriesNumber"])
		self.period()

	def loc(self, loc):
		sep = ""
		for unit, val in loc:
			self.add(sep)
			sep = ", "
			if unit:
				sg, pl = cited_range_units[unit]
				abbr = sg
				# XXX not possible to tell unambiguously whether we have several units or not
				if any(c in loc for c in ",-\N{EN DASH}\N{EM DASH}"):
					abbr = pl
				self.add(abbr + "\N{NBSP}")
				# XXX maybe not only for pages?
				if unit == "page":
					val = val.replace("-", "\N{EN DASH}")
			self.add(val)

	def place_publisher_loc(self, rec, params):
		self.space()
		if rec["place"]:
			self.add(rec["place"])
		else:
			self.add("No place")
		publisher = rec.get("publisher")
		if publisher:
			self.add(": ")
			self.add(publisher)
		if params["loc"]:
			self.add(", ")
			self.loc(params["loc"])
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
		self.space()
		self.add("DOI:")
		self.space()
		tag = self.tag("a", {"class": "url", "href": f"https://doi.org/{doi}"})
		tag.append(doi)
		self.add(tag)
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
			self.add("URL:")
		else:
			self.add("URLs:")
		self.space()
		for i, url in enumerate(urls):
			url = config.normalize_url(url)
			tag = self.tag("a", {"class": "url", "href": url})
			tag.append(url)
			self.add(tag)
			if i < len(urls) - 1:
				self.add("; ")
		self.period()

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
}

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
	w.authors(rec)
	w.date(rec)
	w.quoted(rec["title"])
	if rec["publicationTitle"]:
		w.space()
		abbr = rec["journalAbbreviation"]
		name = rec["publicationTitle"]
		# Use the abbreviated journal name if possible. Note that some
		# people set journalAbbreviation = publicationTitle, so in
		# this case ignore the abbreviation.
		if abbr and abbr != name:
			if name:
				name.name = "i"
				tag = w.tag("abbr", {"data-tip": name.xml()})
				tagi = w.tag("i")
				tagi.append(abbr)
				tag.append(tagi)
				w.add(tag)
			else:
				tag = w.tag("i")
				tag.append(abbr)
				w.add(tag)
		else:
			tag = w.tag("i")
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
		if params["loc"]:
			w.add(": ")
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
	w.authors(rec)
	w.date(rec)
	w.italic(rec["title"])
	w.edition(rec)
	w.place_publisher_loc(rec, params)
	w.idents(rec)

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
	w.authors(rec, skip_editors=True)
	w.date(rec)
	w.quoted(rec["title"])
	if rec["proceedingsTitle"]:
		w.space()
		w.add("In: ")
		w.italic(rec["proceedingsTitle"])
	w.edited_by(rec)
	if rec["volume"]:
		w.space()
		w.add("Vol.\N{NBSP}")
		w.add(rec["volume"])
		w.period()
	w.series(rec)
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
	w.authors(rec)
	w.date(rec)
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
	w.authors(rec, skip_editors=True)
	w.date(rec)
	w.quoted(rec["title"])
	if rec["bookTitle"]:
		w.space()
		w.add("In: ")
		w.italic(rec["bookTitle"])
		w.edition(rec)
	w.edited_by(rec)
	if rec["volume"]:
		w.space()
		w.add("Vol.\N{NBSP}")
		w.add(rec["volume"])
		w.period()
	w.series(rec)
	if rec["numberOfVolumes"]:
		w.space()
		w.add(rec["numberOfVolumes"])
		w.space()
		w.add("vols.")
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
	w.authors(rec)
	w.date(rec)
	w.quoted(rec["title"])
	w.space()
	w.add(rec["thesisType"] or "Thesis")
	if rec["university"]:
		w.add(", ")
		w.add(rec["university"])
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
	w.authors(rec)
	w.date(rec)
	w.quoted(rec["title"])
	w.idents(rec)

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
	w.authors(rec)
	w.quoted(rec["title"])
	w.italic(rec["publicationTitle"])
	w.date(rec)
	w.edition(rec)
	w.place_publisher_loc(rec, params)
	w.idents(rec)

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
	w.authors(rec)
	w.date(rec)
	w.quoted(rec["title"])
	if rec["repository"]:
		w.space()
		w.add(rec["repository"])
		w.period()
	if params["loc"]:
		w.loc(params["loc"])
		w.period()
	w.idents(rec)

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
		if tag.name not in valid_tags and tag.parent:
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
		if node.type == "string":
			yield node
		elif node.type == "tag":
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
	# XXX can't replace & with &amp; in <a href="..."/>
	# XXX shouldn't replace &lt; and instead of &gt;
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
	date = rec.get("date")
	if date:
		# Always use "-"
		date = date.replace("\N{en dash}", "-")
		# The ZG prescribes to use n.d."
		if re.match(r"^n\.\s?d\.?$", date, re.I):
			date = None
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
			publisher = None
		rec["publisher"] = publisher
	for key, value in rec.copy().items():
		if key in ("filename", "itemType", "pages", "url", "DOI", "callNumber"): # XXX figure out other "id" fields
			continue
		if isinstance(value, str):
			rec[key] = fix_value(value)
			continue
		if key != "creators":
			continue
		assert key == "creators", key
		for creator in value:
			for field in ("firstName", "lastName", "name"):
				val = creator.get(field)
				if not val:
					continue
				creator[field] = fix_value(val)

# TODO generate ref and entries with 1918a, 1918b, etc. when necessary

def invalid_entry(ref, reason, key=None):
	r = tree.parse_string('<p class="bib-entry"/>').root
	if key:
		r["id"] = f"bib-key-{key}"
	span = r.tree.tag("span", **{"class": "bib-ref-invalid"})
	span["data-tip"] = reason
	span.append(ref)
	r.append(span)
	return r.xml()

def fix_loc(rec, loc):
      page = rec.get("pages")
      if not page:
              return
      for i, (unit, val) in enumerate(loc):
              loc[i] = (unit, val)
              if unit == "page":
                      return
      loc.insert(0, ("page", page))

def get_entry(ref, **params):
	db = config.db("texts")
	recs = db.execute("select key, json ->> '$.data' from biblio_data where short_title = ?", (ref,)).fetchall()
	if len(recs) == 0:
		return invalid_entry(ref, "Not found in bibliography")
	if len(recs) > 1:
		return invalid_entry(ref, "Multiple bibliographic entries bear this short title")
	key, rec = recs[0]
	rec = json.loads(rec)
	f = renderers.get(rec["itemType"])
	if not f:
		return invalid_entry(ref, "Entry type '%s' not supported" % rec["itemType"], key)
	return format_entry(key, rec, **params)

def format_entry(key, rec, **params):
	f = renderers[rec["itemType"]]
	fix_rec(rec)
	fix_loc(rec, params["loc"])
	w = Writer()
	w.xml["id"] = f"bib-key-{key}"
	if params["n"]:
		tag = w.tag("b")
		tag.append("[")
		tag.append(params["n"])
		tag.append("]")
		w.add(tag)
		w.space()
	f(rec, w, params)
	w.space()
	tag = w.tag("i", {"class": "fas fa-edit", "style": "display:inline;color:black;", "data-tip": "Edit on zotero.org"})
	tag.append(" ")
	lnk = w.tag("a", href=f"https://www.zotero.org/groups/1633743/erc-dharma/items/{key}")
	lnk.append(tag)
	w.add(lnk)
	return w.output()

def invalid_ref(ref, reason, missing=False):
	r = tree.parse_string('<a class="nav-link bib-ref-invalid"/>').root
	r["data-tip"] = reason
	r.append(ref)
	return r.xml()

PER_PAGE = 100

def page_of(key):
	db = config.db("texts")
	(index,) = db.execute("""select pos - 1
		from (select row_number() over(order by sort_key) as pos,
			key from biblio_data where sort_key is not null)
		where key = ?""", (key,)).fetchone()
	return (index + PER_PAGE - 1) // PER_PAGE

def get_ref(ref, **params):
	db = config.db("texts")
	recs = db.execute("select key, json ->> '$.data' from biblio_data where short_title = ?", (ref,)).fetchall()
	if len(recs) == 0:
		return invalid_ref(ref, "Not found in bibliography")
	if len(recs) > 1:
		return invalid_ref(ref, "Multiple bibliographic entries bear this short title")
	key, rec = recs[0]
	rec = json.loads(rec)
	fix_rec(rec)
	w = Writer()
	w.xml.name = "span"
	w.xml.attrs.clear()
	tag = w.tag("a", {"class": "bib-ref"})
	if params["missing"]:
		page = page_of(key)
		tag["href"] = f"/bibliography/page/{page}#bib-key-{key}"
	else:
		tag["href"] = f"#bib-key-{key}"
	w.xml.append(tag)
	w.xml = tag
	siglum = params.get("siglum")
	if siglum:
		tag = w.tag("span")
		w.xml.append(tag)
		w.xml = tag
		w.ref(rec)
		w.xml = w.xml.parent
		w.xml["data-tip"] = tag.xml()
		tag.delete()
		w.add(siglum)
	else:
		if params["missing"]:
			pass
			#w.xml["data-tip"] = "Missing in bibliography"
			#w.xml["class"] += " bib-ref-invalid"
		fmt = params["rend"]
		if fmt == "omitname":
			w.date(rec, end_field=False)
		elif fmt == "ibid":
			tag = w.tag("i")
			tag.append("ibid.")
			w.add(tag)
		elif fmt == "default":
			w.ref(rec)
		else:
			assert 0
	w.xml = w.xml.parent
	if params["loc"]:
		w.add(": ")
		w.loc(params["loc"])
	return w.output()

def sort_key(rec):
	typ = rec["itemType"]
	if typ not in renderers:
		return
	skip_editors = typ == "bookSection"
	key = ""
	for creator in rec["creators"]:
		if skip_editors and creator["creatorType"] == "editor":
			continue
		author = creator.get("lastName") or creator.get("name")
		key += author + " " + rec.get("date") + " "
		break
	key += rec["title"] + " " + rec["key"]
	return config.COLLATOR.getSortKey(key)

# XXX must be run when changing the "sort_key" func
@config.transaction("texts")
def update_sort_keys():
	db = config.db("texts")
	db.execute("begin")
	for key, rec in db.execute("select key, json -> '$.data' from biblio_data"):
		rec = json.loads(rec)
		db.execute("update biblio_data set sort_key = ? where key = ?", (sort_key(rec), key))
	db.execute("commit")

if __name__ == "__main__":
	update_sort_keys()
	#params = {"rend": "default", "loc": [], "n": "", "missing": False}
	#r = get_entry(sys.argv[1], **params)
	pass
