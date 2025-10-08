# For ISO 639-3 (languages), the authority is https://iso639-3.sil.org
# For ISO 639-5 (language families), the authority is
# https://www.loc.gov/standards/iso639-5/index.html

"""TODO

While processing a tree, need to gather the following info for displaying
div[@type='edition']: (a) all langs (b) all scripts (c) for each lang, scripts
it is associated with (d) for each script, langs is it associated with.

In addition, should have stats (number of chars, of clusters, etc.) for each
lang, script, pair of script+lang. But might be easier to fetch the info if we
use the internal representation instead of the TEI one.

Save all this stuff that in the catalog, we will decide what to display later
on.

"""


"""TODO
# XXX we need to treat the apparatus separately when assigning languages. the
# default should be something like "undetermined source language".

only attempt to find @rendition in div[@type='edition'] and in div[@type='apparatus']
(because we will need transliteration there). ignore @rendition in other locations.
should use the same rule we use for languages, for simplicity. but we don't
need the distinction assigned/inferred for scripts.

pair (language,script)

should assume that scripts are inherited, but are set to "undefined"
when in a foreign element, and maybe when the language changes.

change category names in the main table:
  arabic -> arabic_other
  brāhmī -> brāhmī_other
  brāhmī_northern -> brāhmī_northern_other
  brāhmī_southeast
  brāhmī_southern

what should we do with the script hierarchy? can store it in a sql table,
but in this case add something for converting this to a json doc.

add a script table to the website, as we did for languages

in the metadata display, print script information.
"""

import sys, functools, collections
import requests # pip install requests
from dharma import common, texts, tree

# Scripts data pulled from opentheso
# To link to opentheso, use addresses of the form:
# https://opentheso.huma-num.fr/opentheso/?idc={classID}&idt={thesaurusID}
# The thesaurusID of dharma is th347.

Script = collections.namedtuple("Script", "level id name klass")
ScriptMaturity = collections.namedtuple("ScriptMaturity", "id name klass")

null_script = Script(0, "undetermined", "Undetermined", 0)

scripts = (
	Script(0, "arabic", "Arabic", 57471),
		Script(1, "jawi", "Jawi", 70417),
	Script(0, "brāhmī", "Brāhmī and derivatives", 83217),
		Script(1, "brāhmī_northern", "Northern class Brāhmī", 83223),
			Script(2, "bhaikṣukī", "Bhaikṣukī", 84158),
			Script(2, "gauḍī", "Gauḍī", 83229),
			Script(2, "nāgarī", "Nāgarī", 38771),
			Script(2, "siddhamātr̥kā", "Siddhamātr̥kā", 38774),
		Script(1, "brāhmī_southeast_asian", "Southeast Asian Brāhmī", 83227),
			Script(2, "balinese", "Balinese", 83239),
			Script(2, "batak", "Batak", 38767),
			Script(2, "cam", "Cam", 83233),
			Script(2, "kawi", "Kawi", 38769),
			Script(2, "khmer", "Khmer", 83231),
			Script(2, "mon-burmese", "Mon-Burmese", 83235),
			Script(2, "javanese_old_west", "Old West Javanese", 83241),
			Script(2, "pyu", "Pyu", 83237),
			Script(2, "sundanese", "Sundanese", 57470),
		Script(1, "brāhmī_southern", "Southern class Brāhmī", 83225),
			Script(2, "grantha", "Grantha", 38768),
			Script(2, "kannada", "Kannada", 82857),
			Script(2, "tamil", "Tamil", 38776),
			Script(2, "telugu", "Telugu", 81340),
			Script(2, "vaṭṭeḻuttu", "Vaṭṭeḻuttu", 70420),
			Script(2, "chinese", "Chinese", 83221),
	Script(0, "kharoṣṭhī", "Kharoṣṭhī", 83219),
	Script(0, "undetermined", "Undetermined", 0),
	null_script,
)

default_script = null_script

null_script_maturity = ScriptMaturity("null", "Null", 0)

scripts_maturity = (
	ScriptMaturity("early", "Early Brāhmī", 83207),
	ScriptMaturity("late", "Late Brāhmī", 83211),
	ScriptMaturity("middle", "Middle Brāhmī", 83209),
	ScriptMaturity("regional", "Regional Brāhmī-derived script", 83213),
	ScriptMaturity("vernacular", "Vernacular Brāhmī-derived script", 83215),
	null_script_maturity,
)

script_from_ident = {
	**{script.id: script for script in scripts},
	**{str(script.klass): script for script in scripts},
}
def get_script(ident):
	return script_from_ident.get(ident, null_script)

script_maturity_from_ident = {
	**{script.id: script for script in scripts_maturity},
	**{str(script.klass): script for script in scripts_maturity},
}
def get_script_maturity(ident):
	return script_maturity_from_ident.get(ident, null_script_maturity)

Pair = collections.namedtuple("Pair", "lang script children")

AltLang = collections.namedtuple("AltLang", "lang children")

def alloc_lang(ctx, node, dflt):
	lang = lang_attr(node)
	if not lang:
		return dflt
	ret = ctx.get(lang)
	if not ret:
		tmp = Language(lang)
		ret = ctx.get(tmp.id)
		if not ret:
			ret = tmp
			ctx[ret.id] = ret
	return ret

def alloc_script(ctx, node, dflt):
	script = script_attr(node)
	if not script:
		return dflt
	ret = ctx.get(script)
	if not ret:
		tmp = Script(script)
		ret = ctx.get(tmp.id)
		if not ret:
			ret = tmp
			ctx[ret.id] = ret
	return ret

# For assigning languages, we follow the basic inheritance rule: if a tag does
# not have an @xml:lang, it is assigned the language assigned its parent. But
# there are exceptions:
# * If the tag is "lem" or "rdg" and does not have an @xml:lang, we assign it
#   the language it would be assigned if it occurred in the edition div, under
#   the same textparts (if any). We only expect to find "lem" and "rdg" in the
#   apparatus.
# * If the tag is "foreign" and does not have an @xml:lang, we assume it is in
#   some source language (as per the guide) and assign it a generic language
#   code named "source" that represents any source language (per contrast with
#   languages used in translations) viz. the union of all source languages.
#
# Furthermore, we store two language values per node:
# * Inherited language. Assigned when traversing the tree top-down. This follows
#   what people have indicated.
# * Inferred language. Assigned by bubbling up language values bottom-up. This
#   value is intended to be used for text processing (tokenization, etc.).
# If e.g. the original XML is <a lang="eng"><b lang="fra"><c>foo</c></b></a>
# the inherited language of <c> is "fra"; and the inferred language of <a> is
# "fra", even though the user assigned it the language "eng", because it only
# contains French text.

def lang_attr(node):
	return node["lang"].split("-")[0]

def script_attr(node):
	for field in node["rendition"].split():
		val = field.removeprefix("class:")
		if val:
			return val
	return ""

def fetch_alt_langs(ctx, node, default_lang):
	path = "TEI/text/body/div[@type='edition']".split("/")
	lang = default_lang
	for name in path:
		node = node.first(name)
		if not node:
			return AltLang(lang, {})
		lang = alloc_lang(ctx, node, lang)
	final = AltLang(lang, {})
	stack = [(node, final)]
	while stack:
		node, struct = stack.pop()
		for child in node.find("div[@type='textpart' and @n]"):
			n = child["n"]
			lang = alloc_lang(ctx, child, struct.lang)
			child_struct = AltLang(lang, {})
			struct.children[n] = child_struct
			stack.append((child, child_struct))
	return final

def wait_div(ctx, node, parent_lang, alt_lang, f):
	assert f is wait_div
	if node.name == "div":
		if node["type"] in ("edition", "apparatus"):
			f = wait_textpart
		else:
			f = assign_language
	assign_language(ctx, node, parent_lang, alt_lang, f)

def wait_textpart(ctx, node, parent_lang, alt_lang, f):
	assert f is wait_textpart
	if node.matches("div[@type='textpart' and @n]"):
		n = node["n"]
		child_lang = alt_lang.children.get(n)
		if not child_lang:
			child_lang = AltLang(alt_lang.lang, {})
			alt_lang.children[n] = child_lang
		alt_lang = child_lang
	else:
		f = assign_language
	assign_language(ctx, node, parent_lang, alt_lang, f)

def assign_language(ctx, node, parent_lang, alt_lang, f):
	match node.name:
		case "lem" | "rdg":
			lang = alloc_lang(ctx, node, alt_lang.lang)
		case "foreign":
			lang = alloc_lang(ctx, node, Source)
		case "g":
			node.assigned_lang = node.inferred_lang = alloc_lang(ctx, node, parent_lang)
			return
		case _:
			lang = alloc_lang(ctx, node, parent_lang)
	node.assigned_lang = lang
	langs = set()
	for child in node:
		match child:
			case tree.String() if not child.isspace():
				child.assigned_lang = child.inferred_lang = lang
			case tree.Tag():
				f(ctx, child, lang, alt_lang, f)
			case _:
				continue
		langs.add(child.inferred_lang)
	if len(langs) == 1:
		lang = langs.pop()
	node.inferred_lang = lang

def assign_languages(t):
	ctx = {}
	dflt = Language("eng")
	alt_lang = fetch_alt_langs(ctx, t, dflt)
	wait_div(ctx, t.root, dflt, alt_lang, wait_div)

def fetch_tsv(file):
	"""Fetch a TSV file from some given source. `file` can be: a
	`texts.File` object, an absolute file path like `/foo/bar.tsv`, or an
	URL like `https://foo.com/bar.tsv`. Returns a list of rows, where each
	row is a `dict` mapping field names to field values in the given row.

        TODO: Should also store a local copy of files we fetch from the web
        (e.g. the iso639 data), in a cache, within the same db. this cache would
        be written to only by change.py, when processing files.
	"""
	if isinstance(file, texts.File):
		text = file.text
	elif file.startswith("/"):
		with open(file) as f:
			text = f.read()
	else:
		r = requests.get(file)
		r.raise_for_status()
		text = r.text
	lines = text.splitlines()
	fields = lines[0].split("\t")
	ret = []
	for line in lines[1:]:
		items = [x.strip() for x in line.split("\t")]
		# Fill with empty values in case lines were rstripped.
		while len(items) < len(fields):
			items.append("")
		if len(items) > len(fields):
			raise Exception("bad format")
		row = zip(fields, items)
		ret.append(dict(row))
	return ret

def add_to_index(code, index, rec):
	if not code:
		return
	assert not code in index or index[code] is rec
	index[code] = rec

def load_data():
	tbl3 = fetch_tsv("https://iso639-3.sil.org/sites/iso639-3/files/downloads/iso-639-3.tab")
	tbl3_bis = fetch_tsv("https://iso639-3.sil.org/sites/iso639-3/files/downloads/iso-639-3_Name_Index.tab")
	tbl5 = fetch_tsv("http://id.loc.gov/vocabulary/iso639-5.tsv")
	tbl0 = fetch_tsv(texts.save("project-documentation", "DHARMA_languages.tsv"))
	recs = []
	index = {}
	for row in tbl3:
		rec = {
			"id": row["Id"],
			"name": row["Ref_Name"],
			"iso": 3,
			"custom": False,
			"dharma": False,
			"source": True,
		}
		recs.append(rec)
		# "Part2b", "Part2t", "Part1" are alternate language codes.
		for field in ("Id", "Part2b", "Part2t", "Part1"):
			add_to_index(row[field], index, rec)
	for row in tbl3_bis:
		rec = index[row["Id"]]
		if rec["name"] == row["Print_Name"]:
			assert not rec.get("inverted_name")
			rec["inverted_name"] = row["Inverted_Name"]
	for row in tbl5:
		rec = {
			"id": row["code"],
			"name": row["Label (English)"],
			"inverted_name": row["Label (English)"],
			"iso": 5,
			"custom": False,
			"dharma": False,
			"source": True,
		}
		recs.append(rec)
		add_to_index(rec["id"], index, rec)
	for row in tbl0:
		assert not "-" in row["Id"]
		rec = index.get(row["Id"])
		if not rec:
			rec = {
				"id": row["Id"],
				"name": row["Print_Name"],
				"inverted_name": row["Inverted_Name"],
				"iso": None,
				"custom": True,
				"dharma": True,
				"source": True,
			}
			recs.append(rec)
			add_to_index(rec["id"], index, rec)
		elif row["Print_Name"] != rec["name"] or row["Inverted_Name"] != rec["inverted_name"]:
			rec["name"] = row["Print_Name"]
			rec["inverted_name"] = row["Inverted_Name"]
			rec["custom"] = True
			rec["source"] = common.to_boolean(row["source"], True)
		else:
			rec["source"] = common.to_boolean(row["source"], True)
		rec["dharma"] = True
	assert all("inverted_name" in rec for rec in recs)
	recs.sort(key=lambda rec: rec["id"])
	return recs, index

def from_code(s):
	db = common.db("texts")
	(ret,) = db.execute("""select name
		from langs_list natural join langs_by_code
		where code = ?
		""", (s,)).fetchone() or (None,)
	return ret

lang_data = collections.namedtuple("lang_data", "id name inverted_name source")
default_lang = lang_data("und", "Undetermined", "Undetermined", True) # XXX need this to actually exist in the DB!

script_data = collections.namedtuple("script_data", "id name inverted_name opentheso_id")
default_script = script_data("undetermined", "Undetermined", "Undetermined", 0)

@functools.total_ordering
class Script2:

	def __init__(self, key):
		self.key = key
		self._data = None

	def _fetch(self):
		ret = self._data
		if not ret:
			db = common.db("texts")
			ret = db.execute("""
			select id, name, inverted_name, opentheso_id
			from scripts_list
			where id = ? or opentheso_id = ?
			""", (self.key,)).fetchone()
			if ret:
				ret = script_data(ret["id"], ret["name"],
					ret["inverted_name"], ret["opentheso_id"])
			else:
				ret = default_script
			self._data = ret
		return ret

	def __str__(self):
		return self.name

	def __repr__(self):
		return f"Script({self.key})"

	@property
	def id(self):
		return self._fetch().id

	@property
	def name(self):
		return self._fetch().name

	@property
	def inverted_name(self):
		return self._fetch().inverted_name

	@property
	def opentheso_id(self):
		return self._fetch().opentheso_id

	def __hash__(self):
		return hash(self.id)

	def __lt__(self, other):
		return self.inverted_name < other.inverted_name

	def __eq__(self, other):
		return self.id == other.id

@functools.total_ordering
class Language:

	def __init__(self, key):
		self.key = key
		self._data = None

	def _fetch(self):
		ret = self._data
		if not ret:
			db = common.db("texts")
			ret = db.execute("""
			select id, name, inverted_name, source
			from langs_list natural join langs_by_code
			where code = ?
			""", (self.key,)).fetchone()
			if ret:
				ret = lang_data(ret["id"], ret["name"],
					ret["inverted_name"], ret["source"])
			else:
				ret = default_lang
			self._data = ret
		return ret

	def __str__(self):
		return self.name

	def __repr__(self):
		return f"Lang({self.key})"

	@property
	def id(self):
		return self._fetch().id

	@property
	def name(self):
		return self._fetch().name

	@property
	def inverted_name(self):
		return self._fetch().inverted_name

	@property
	def is_source(self):
		return self._fetch().source

	def __hash__(self):
		return hash(self.id)

	def __lt__(self, other):
		return self.inverted_name < other.inverted_name

	def __eq__(self, other):
		if isinstance(other, str):
			return self.id == other
		return self.id == other.id

def make_db():
	db = common.db("texts")
	recs, index = load_data()
	db.execute("delete from langs_by_code")
	db.execute("delete from langs_by_name")
	db.execute("delete from langs_list")
	for rec in recs:
		db.execute("""
			insert into langs_list(id, name, inverted_name, iso,
				custom, dharma, source)
			values(:id, :name, :inverted_name, :iso,
				:custom, :dharma, :source)""", rec)
		db.execute("insert into langs_by_name(id, name) values(?, ?)",
			(rec["id"], common.normalize_text(rec["name"])))
	for code, rec in sorted(index.items()):
		db.execute("insert into langs_by_code(code, id) values(?, ?)", (code, rec["id"]))

Undetermined = Language("und")
Undetermined._data = default_lang

Source = Language("source")
Source._data = lang_data("source", "Source", "Source", True) # XXX need to exist in the DB!

@common.transaction("texts")
def main():
	t = tree.parse(sys.stdin)
	assign_languages(t)
	for node in t.find("//*"):
		print(node.path, node.assigned_lang, node)

def print_scripts():
	for script in scripts:
		print(f'<valItem ident="class:{script.klass:0{5}}"><desc>{script.name}</desc></valItem>')
		print(f'<valItem ident="class:{script.id}"><desc>{script.name}</desc></valItem>')
	for script in scripts_maturity:
		print(f'<valItem ident="maturity:{script.klass:0{5}}"><desc>{script.name}</desc></valItem>')
		print(f'<valItem ident="maturity:{script.id}"><desc>{script.name}</desc></valItem>')


scripts_list = [
	[("arabic", "Arabic", 57471),
		("jawi", "Jawi", 70417)
	],
	[("brāhmī", "Brāhmī", 83217, "Brāhmī"),
		[("brāhmī_northern", "Northern Brāhmī", 83223, "Brāhmī, Northern"),
			("bhaikṣukī", "Bhaikṣukī", 84158),
			("gauḍī", "Gauḍī", 83229),
			("nāgarī", "Nāgarī", 38771),
			("siddhamātr̥kā", "Siddhamātr̥kā", 38774)],
		[("brāhmī_southeast_asian", "Southeast Asian Brāhmī", 83227, "Brāhmī, Southeast Asian"),
			("balinese", "Balinese", 83239),
			("batak", "Batak", 38767),
			("cam", "Cam", 83233),
			("kawi", "Kawi", 38769),
			("khmer", "Khmer", 83231),
			("mon-burmese", "Mon-Burmese", 83235),
			("javanese_old_west", "Old West Javanese", 83241, "Javanese, Old West"),
			("pyu", "Pyu", 83237),
			("sundanese", "Sundanese", 57470)],
		[("brāhmī_southern", "Southern Brāhmī", 83225, "Brāhmī, Southern"),
			("grantha", "Grantha", 38768),
			("kannada", "Kannada", 82857),
			("tamil", "Tamil", 38776),
			("telugu", "Telugu", 81340),
			("vaṭṭeḻuttu", "Vaṭṭeḻuttu", 70420),
			("chinese", "Chinese", 83221)],
	],
	("kharoṣṭhī", "Kharoṣṭhī", 83219),
	("undetermined", "Undetermined", 0),
]
@common.transaction("texts")
def insert_scripts():
	db = common.db("texts")
	db.execute("delete from scripts_list")
	def inner(scripts, parent):
		for items in scripts:
			if isinstance(items, list):
				script = items[0]
			else:
				script = items
			if len(script) == 3:
				ident, name, opentheso_id = script
				inverted_name = name
			elif len(script) == 4:
				ident, name, opentheso_id, inverted_name = script
			db.execute("""
			insert into scripts_list(id, name, inverted_name, opentheso_id)
			values(?, ?, ?, ?)""", (ident, name, inverted_name, opentheso_id))
			if isinstance(items, list):
				inner(items[1:], ident)
	inner(scripts_list, None)

if __name__ == "__main__":
	insert_scripts()
