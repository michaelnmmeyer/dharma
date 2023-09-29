# When processing a text, oxygen generates zotero API calls like this:
# https://api.zotero.org/groups/1633743/items?tag=ROD1914&format=tei
# This is why tags are used, but can we generate another API call that uses a
# proper primary key? Yes, use:
# https://api.zotero.org/groups/1633743/items/ZZH5G8PB?format=tei

import json, unicodedata, html, re, time
import warnings
from collections import OrderedDict
import requests
from bs4 import BeautifulSoup, Tag, MarkupResemblesLocatorWarning
from dharma import config

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
	json json not null
);
commit;
"""
conn = config.open_db("biblio", SCHEMA)

def sort_value(val):
	if not isinstance(val, dict):
		return val
	vals = sorted((k, sort_value(v)) for k, v in val.items())
	return OrderedDict(vals)

def to_json(val):
	val = sort_value(val)
	return json.dumps(val, separators=(",", ":"), ensure_ascii=False)

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

@conn.transaction
def update():
	conn.execute("begin immediate")
	(max_version,) = conn.execute("select value from meta where key = 'latest_version'").fetchone()
	ret = []
	for entry in zotero_items(max_version, ret):
		doc = to_json(entry)
		conn.execute("""insert or replace into bibliography(key, version, json)
			values(?, ?, ?)""", (entry["key"], entry["version"], doc))
	assert len(ret) == 1
	conn.execute("update meta set value = ? where key = 'latest_version'", (ret[0],))
	conn.execute("commit")

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
	for (entry,) in conn.execute("select json from bibliography"):
		entry = json.loads(entry)
		for val in all_string_values(entry, ignore=set()):
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

if __name__ == "__main__":
	check_entries()
