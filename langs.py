# For ISO 639-3 (languages), the authority is https://iso639-3.sil.org
# For ISO 639-5 (language families), the authority is
# https://www.loc.gov/standards/iso639-5/index.html

import os, sys, functools, collections
import requests # pip install requests
from dharma import config, texts, tree

# Scripts data pulled from opentheso
# To link to opentheso, use https://opentheso.huma-num.fr/opentheso/?idc={classID}&idt={thesaurusID}
# The thesaurusID of dharma is th347.

Script = collections.namedtuple("Script", "level ident name klass")
ScriptMaturity = collections.namedtuple("ScriptMaturity", "ident name klass")

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
	Script(2, "tamil", "Tamil", 57475), # was "Tamil with Grantha", now deleted
	Script(2, "telugu", "Telugu", 81340),
	Script(2, "vaṭṭeḻuṭṭu", "Vaṭṭeḻuṭṭu", 70420),
	Script(2, "chinese", "Chinese", 83221),
	Script(0, "kharoṣṭhī", "Kharoṣṭhī", 83219),
	Script(0, "undetermined", "Undetermined", 0),
)

scripts_maturity = (
	ScriptMaturity("early", "Early Brāhmī", 83207),
	ScriptMaturity("late", "Late Brāhmī", 83211),
	ScriptMaturity("middle", "Middle Brāhmī", 83209),
	ScriptMaturity("regional", "Regional Brāhmī-derived script", 83213),
	ScriptMaturity("vernacular", "Vernacular Brāhmī-derived script", 83215),
	ScriptMaturity("null", "Null", 0),
)

script_from_class = {script.klass: script for script in scripts}
script_from_ident = {script.ident: script for script in scripts}

AltLang = collections.namedtuple("AltLang", "lang children")

def alloc_lang(ctx, lang, dflt):
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

def fetch_alt_langs(ctx, node, default_lang):
	path = ["TEI", "text", "body", "div[@type='edition']"]
	lang = default_lang
	for name in path:
		node = node.first(name)
		if not node:
			return AltLang(lang, {})
		lang = alloc_lang(ctx, node["lang"], lang)
	final = AltLang(lang, {})
	stack = [(node, final)]
	while stack:
		node, struct = stack.pop()
		for child in node.children():
			if child.name == "div" and child["type"] == "textpart" and child["n"]:
				n = child["n"]
				lang = alloc_lang(ctx, child["lang"], struct.lang)
				child_struct = AltLang(lang, {})
				struct.children[n] = child_struct
				stack.append((child, child_struct))
	return final

def wait_div(ctx, node, parent_lang, alt_lang, f):
	assert f is wait_div
	if node.name == "div":
		if node["type"] in ("edition", "apparatus", "translation", "commentary"):
			f = wait_textpart
		else:
			f = assign_language
	assign_language(ctx, node, parent_lang, alt_lang, f)

def wait_textpart(ctx, node, parent_lang, alt_lang, f):
	assert f is wait_textpart
	if node.name == "div" and node["type"] == "textpart" and node["n"]:
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
			lang = alloc_lang(ctx, node["lang"], alt_lang.lang)
		case "foreign":
			lang = alloc_lang(ctx, node["lang"], alt_lang.lang)
			if lang == parent_lang:
				node.add_warning(f'''Element "foreign" is in language {lang!r}, which is the same as its parent element. You might have forgotten to add an @xml:lang to div[@type='edition'] or its children text div[@type='textpart']. You might also need to add an explicit @xml:lang to this "foreign" element.''')
		case "g":
			node.lang = alloc_lang(ctx, node["lang"], parent_lang)
			return
		case _:
			lang = alloc_lang(ctx, node["lang"], parent_lang)
	langs = set()
	for child in node:
		match child:
			case tree.String() if not child.isspace():
				child.lang = lang
			case tree.Tag():
				f(ctx, child, lang, alt_lang, f)
			case _:
				continue
		langs.add(child.lang)
	if len(langs) == 1:
		lang = langs.pop()
	node.lang = lang

def assign_languages(t):
	ctx = {}
	dflt = Language("eng")
	alt_lang = fetch_alt_langs(ctx, t, dflt)
	wait_div(ctx, t.root, dflt, alt_lang, wait_div)

# Should also store a local copy of files we fetch from the web (e.g. the iso639
# data), in a cache, within the same db. this cache would be written to only by
# change.py, when processing files.
def fetch_tsv(file):
	if isinstance(file, texts.File):
		text = file.text
	elif file.startswith("/"):
		with open(url) as f:
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

def to_boolean(s, dflt):
	match s.lower():
		case "true" | "yes" | "on" | "1":
			return True
		case "false" | "no" | "off" | "0":
			return False
		case _:
			return dflt

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
			rec["source"] = to_boolean(row["source"], True)
		else:
			rec["source"] = to_boolean(row["source"], True)
		rec["dharma"] = True
	assert all("inverted_name" in rec for rec in recs)
	recs.sort(key=lambda rec: rec["id"])
	return recs, index

def from_code(s):
	db = config.db("texts")
	(ret,) = db.execute("""select name
		from langs_list natural join langs_by_code
		where code = ?
		""", (s,)).fetchone() or (None,)
	return ret

lang_data = collections.namedtuple("lang_data", "id name inverted_name source")
default_lang = lang_data("und", "Undetermined", "Undetermined", True) # XXX need this to actually exist in the DB!

@functools.total_ordering
class Language:

	def __init__(self, key):
		self.key = key
		self._data = None

	def _fetch(self):
		ret = self._data
		if not ret:
			db = config.db("texts")
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
		return self.inverted_name == other.inverted_name

def make_db():
	db = config.db("texts")
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
			(rec["id"], config.normalize_text(rec["name"])))
	for code, rec in sorted(index.items()):
		db.execute("insert into langs_by_code(code, id) values(?, ?)", (code, rec["id"]))

Undetermined = Language("und")
Undetermined._data = default_lang

@config.transaction("texts")
def main():
	t = tree.parse(sys.stdin)
	assign_languages(t)
	for node in t.find("//*"):
		print(node.path, node.lang, node)

def print_scripts():
	for script in scripts:
		print(f'<valItem ident="class:{script.klass:0{5}}"><desc>{script.name}</desc></valItem>')
		print(f'<valItem ident="class:{script.ident}"><desc>{script.name}</desc></valItem>')
	for script in scripts_maturity:
		print(f'<valItem ident="maturity:{script.klass:0{5}}"><desc>{script.name}</desc></valItem>')
		print(f'<valItem ident="maturity:{script.ident}"><desc>{script.name}</desc></valItem>')

if __name__ == "__main__":
	main()
