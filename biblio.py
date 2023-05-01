#!/usr/bin/env python3

import os, json, sqlite3, unicodedata, html
import warnings
from collections import OrderedDict

from pyzotero import zotero
from bs4 import BeautifulSoup, Tag, MarkupResemblesLocatorWarning

LIBRARY_ID = 1633743
LIBRARY_TYPE = "group"
MY_API_KEY = "ojTBU4SxEQ4L0OqUhFVyImjq"

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE bibliography(
	key TEXT PRIMARY KEY NOT NULL,
	json TEXT NOT NULL
);
"""

conn = sqlite3.connect("biblio.sqlite")

def sort_value(val):
	if not isinstance(val, dict):
		return val
	vals = sorted((k, sort_value(v)) for k, v in val.items())
	return OrderedDict(vals)

def to_json(val):
	val = sort_value(val)
	return json.dumps(val, separators=(",", ":"), ensure_ascii=False)

def download():
	conn.execute("DROP TABLE IF EXISTS bibliography")
	conn.executescript(SCHEMA)
	lib = zotero.Zotero(LIBRARY_ID, LIBRARY_TYPE, MY_API_KEY)
	bib = lib.everything(lib.top())
	for entry in bib:
		doc = to_json(entry)
		conn.execute("INSERT INTO bibliography VALUES(?, ?)", (entry["key"], doc))
	conn.commit()
	conn.close()

# See https://www.zotero.org/support/kb/rich_text_bibliography
valid_tags = {
	"i": [],
	"b": [],
	"sub": [],
	"sup": [],
	"span": [("style", "font-variant:small-caps;"), ("class", "nocase")],
}

ident_like = {"shortTitle", "tags", "key", "url", "links"}

def all_string_values(obj, ignore=set()):
	if isinstance(obj, str):
		yield obj
	elif isinstance(obj, int):
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

def check_string_value(soup, entry):
	for tag in soup.find_all("em"):
		tag.name = "i"
	for tag in soup.find_all("a"):
		assert "href" in tag.attrs
		href = tag["href"]
		tag.attrs.clear()
		tag["href"] = href
	for tag in soup.find_all(lambda x: isinstance(x, Tag)):
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
			print("%s: bad markup: %r" % (entry["key"], tag))

def check_entries():
	warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)
	for (entry,) in conn.execute("SELECT json FROM bibliography"):
		entry = json.loads(entry)
		for val in all_string_values(entry):
			then = val
			val = unicodedata.normalize("NFC", val)
			if val != then:
				print("%s: not normalized: %r" % (entry["key"], val))
			val = html.unescape(val)
			val = val.replace("&", "&amp;")
			if "\N{NBSP}" in val:
				print("%s: non-breaking space: %r" % (entry["key"], val))
			soup = BeautifulSoup(val, "html.parser")
			if val != str(soup):
				print("%s: escaping issue: %s | %r" % (entry["key"], val, soup))
				continue
			check_string_value(soup, entry)
		for val in all_string_values(entry, ignore=ident_like):
			if "oe" in val.lower() or "ae" in val.lower():
				print("%s: ligatures: %r" % (entry["key"], val))
			# Deal with quotes here or later?

check_entries()
