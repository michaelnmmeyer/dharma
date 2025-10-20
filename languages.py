"Stuff for dealing with languages and scripts"

# For ISO 639-3 (languages), the authority is https://iso639-3.sil.org
# For ISO 639-5 (language families), the authority is
# https://www.loc.gov/standards/iso639-5/index.html

"""TODO

where should we stick lang infos in the internal representation? should have
at least @lang and @script (maybe @maturity). add it to each element, so that
we don't need stateful processing for figuring out languages.

While processing a tree, need to gather the following info for displaying
div[@type='edition']: (a) all langs; (b) all scripts; (c) for each lang, scripts
it is associated with; (d) for each script, langs is it associated with. It is
simpler to do that on the constructed internal representation.

In addition, should have stats (number of chars, of clusters, etc.) for each
lang, script, pair of script+lang. But might be easier to gather stats like this
if we use the internal representation instead of the TEI one.

Save all this stuff that in the catalog, we will decide what to display later
on.

Should print scripts in a specific page, or maybe on the same page as the one
used for langs.

"""

import sys, re, copy
import requests # pip install requests
from dharma import common, texts, tree


######################## For annotating TEI documents ##########################

# We interpret @xml:lang only on these elements. If another element has an
# @xml:lang, we act as if it did not exist, and assign to it the language of its
# parent node.
#
# This must be kept in sync with the TEI parsing code.
#
# The reason we do not take all elements into account is that this would entail
# much modifications to the TEI parsing code (because we would need to pass
# a @lang parameter to most newly created elements).
tei_language_sensitive = {
	"div", "note", "p", "ab", "lg", "q", "head", "quote",
	"label", "foreign", "seg",
}

class LanguageInfo:

	def __init__(self, language="eng", script="latin", maturity="", is_source=False):
		self.language = language
		self.is_source = is_source
		self.script = script
		self.script_maturity = maturity

	def __repr__(self):
		return f"LanguageInfo({self.language}, {self.script}, {self.script_maturity})"

	def _fields(self):
		return (self.language, self.script, self.script_maturity)

	def __eq__(self, other):
		return self._fields() == other._fields()

	def __hash__(self):
		return hash(self._fields())

	def __str__(self):
		return f"{self.language} {self.script}"

	def copy(self):
		import copy
		return copy.copy(self)

def recurse(root):
	match root:
		case tree.Tree():
			root.assigned_lang = LanguageInfo()
			for child in root:
				recurse(child)
		case tree.Tag():
			root.assigned_lang = extract_language(root)
			for child in root:
				recurse(child)
		case _:
			root.assigned_lang = root.parent.assigned_lang
	root.inferred_lang = root.assigned_lang

def language_significant(root):
	match root:
		case tree.Tree():
			raise Exception
		case tree.Tag():
			return True
		case tree.Comment():
			return False
		case tree.String():
			return not root.isspace()
		case tree.Instruction():
			return False

def bubble_up(root):
	match root:
		case tree.Branch():
			for child in root:
				bubble_up(child)
			langs = set()
			for child in root:
				if not language_significant(child):
					continue
				langs.add(child.inferred_lang)
			if len(langs) == 1:
				root.inferred_lang = langs.pop()
		case _:
			pass

def extract_language(node):
	if node.assigned_lang:
		return node.assigned_lang
	if node.name not in tei_language_sensitive:
		return node.parent.assigned_lang
	lang_id = node["lang"].split("-")[0]
	script_elems = node["rendition"].split()
	script_id = script_maturity = ""
	is_source = None
	for elem in script_elems:
		if elem.startswith("class:"):
			tmp = elem.removeprefix("class:")
			if tmp == "undetermined":
				tmp = ""
			script_id = tmp
		if elem.startswith("maturity:"):
			tmp = elem.removeprefix("maturity:")
			if re.fullmatch(r"0+", tmp) or tmp == "undetermined":
				tmp = ""
			script_maturity = tmp
	# We inherit separately: language and script, but _not_ the script
	# maturity if it stands on its own.
	if lang_id:
		db = common.db("texts")
		lang_id, is_source = db.execute("""
			select langs_list.id, langs_list.source
			from langs_list join langs_by_code
				on langs_list.id = langs_by_code.id
			where langs_by_code.code = ?""",
			(lang_id,)).fetchone() or ("und", False)
	if script_id:
		db = common.db("texts")
		(script_id,) = db.execute("""select id from scripts_by_code
			where code = ?""", (script_id,)).fetchone() or ("any_other",)
	if not lang_id and not script_id:
		return node.parent.assigned_lang
	infos = node.parent.assigned_lang.copy()
	if lang_id:
		infos.language = lang_id
		infos.is_source = is_source
	if script_id:
		infos.script = script_id
		if script_maturity:
			infos.script_maturity = script_maturity
		else:
			infos.script_maturity = ""
	if infos != node.parent.assigned_lang:
		return infos
	return node.parent.assigned_lang

def assign_languages(t):
	"""For assigning languages, we follow the basic inheritance rule: if a
        tag does not have an @xml:lang, it is assigned the language assigned its
        parent. But there are exceptions:

        ¶ If the tag is "foreign" and does not have an @xml:lang, we assume it
        is in some source language (as per the guide) and assign it a generic
        language named "source" and a script named "source" as well. These
        represent any source language (per contrast with languages used in
        translations).

	Furthermore, we store two language values per node:

	¶ Assigned language. Assigned when traversing the tree top-down. This
        follows what people explicitly indicate for @xml:lang.

	¶ Inferred language. Assigned by bubbling up language values bottom-up.
        This value is intended to be used for text processing (tokenization,
        etc.). If e.g. the original XML is <a lang="eng"><b
        lang="fra"><c>foo</c></b></a> the inherited language of <c> is "fra";
        and the inferred language of <a> is "fra", even though the user assigned
        it the language "eng", because it only contains French text.
	"""
	for node in t.find("//foreign[not @lang]"):
		node.assigned_lang = LanguageInfo(language="und", script="source_other")
	recurse(t)
	bubble_up(t)

##################### For annotating internal documents ########################

# Assign a language attribute to all these tags, and only to them. In any
# case, we need tags that might contain plain text to have a language tag, so
# that, to check the language of any piece of text, we only need to check the
# language assigned to its parent element.
internal_language_accepting = {
	"edition", "apparatus", "translation", "commentary", "bibliography",
	"summary", "hand", "title",
	"div", "head", "quote", "source", "note", "para", "verse",
	"span", "link", "display",
}

def complete_internal(t):
	add_language_info(t)

def add_language_info(node, lang="eng latin"):
	match node:
		case tree.Tree():
			for child in node:
				add_language_info(child)
		case tree.Tag():
			if node.name in internal_language_accepting:
				if node["lang"]:
					lang = node["lang"]
				else:
					node["lang"] = lang
			else:
				assert not node["lang"], node.xml()
			for child in node:
				add_language_info(child, lang)
		case _:
			pass


############################ Database access ###################################

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
		assert row["Id"]
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

class Script:

	def __init__(self, id, opentheso_id, name, inverted_name, children=[],
		source=True):
		self.id = id
		self.opentheso_id = opentheso_id
		self.name = name
		self.inverted_name = inverted_name
		self.children = children
		self.source = source

# In our TEI encoding, people have the option to use a non-leaf script category
# (like "arabic") or a leaf script category (like "jawi"). For search, we want
# all assigned scripts to be leaves. Thus, for the internal representation, we
# create complementary categories in such a way that all branches have a
# complementary leaf. For "arabic", we thus have two subcategories "jawi" and
# "arabic_other"; the latter is used when the user indicated "arabic", so that
# the identifier "arabic" remains available for search and does mean "anything
# in arabic, whether jawi or not".
scripts_hierarchy = Script("any", 0, "Any", "Any", children=[
	Script("source", 0, "Source Script", "Source Script", children=[
		Script("arabic", 57471, "Arabic", "Arabic", children=[
			Script("jawi", 70417, "Jawi", "Jawi"),
		]),
		Script("brāhmī", 83217, "Brāhmī", "Brāhmī", children=[
			Script("brāhmī_northern", 83223, "Northern Brāhmī", "Brāhmī, Northern", children=[
				Script("bhaikṣukī", 84158, "Bhaikṣukī", "Bhaikṣukī"),
				Script("gauḍī", 83229, "Gauḍī", "Gauḍī"),
				Script("nāgarī", 38771, "Nāgarī", "Nāgarī"),
				Script("siddhamātr̥kā", 38774, "Siddhamātr̥kā", "Siddhamātr̥kā"),
			]),
			Script("brāhmī_southeast_asian", 83227, "Southeast Asian Brāhmī", "Brāhmī, Southeast Asian", children=[
				Script("balinese", 83239, "Balinese", "Balinese"),
				Script("batak", 38767, "Batak", "Batak"),
				Script("cam", 83233, "Cam", "Cam"),
				Script("kawi", 38769, "Kawi", "Kawi"),
				Script("khmer", 83231, "Khmer", "Khmer"),
				Script("mon-burmese", 83235, "Mon-Burmese", "Mon-Burmese"),
				Script("javanese_old_west", 83241, "Old West Javanese", "Javanese, Old West"),
				Script("pyu", 83237, "Pyu", "Pyu"),
				Script("sundanese", 57470, "Sundanese", "Sundanese"),
			]),
			Script("brāhmī_southern", 83225, "Southern Brāhmī", "Brāhmī, Southern", children=[
				Script("grantha", 38768, "Grantha", "Grantha"),
				Script("kannada", 82857, "Kannada", "Kannada"),
				Script("tamil", 38776, "Tamil", "Tamil"),
				Script("telugu", 81340, "Telugu", "Telugu"),
				Script("vaṭṭeḻuttu", 70420, "Vaṭṭeḻuttu", "Vaṭṭeḻuttu"),
			]),
		]),
		Script("chinese", 83221, "Chinese", "Chinese"),
		Script("kharoṣṭhī", 83219, "Kharoṣṭhī", "Kharoṣṭhī"),
	]),
	Script("latin", 0, "Latin", "Latin", source=False),
])

def process_scripts(db, script, parent):
	db.execute("""
		insert into scripts_list(id, name, inverted_name, parent, source)
		values(?, ?, ?, ?, ?)""", (script.id, script.name,
		script.inverted_name, parent, script.source))
	if script.children:
		compl = Script(id=script.id + "_other",
			opentheso_id=script.opentheso_id,
			name=script.name + " (other)",
			inverted_name=script.inverted_name + " (other)",
			source=script.source)
		script.children.append(compl)
		db.execute("""insert into scripts_by_code(code, id)
			values(?, ?)""", (script.id, script.id + "_other"))
		for child in script.children:
			process_scripts(db, child, script.id)
	else:
		codes = [script.id]
		if script.opentheso_id:
			codes.append(script.opentheso_id)
		for code in codes:
			db.execute("""insert into scripts_by_code(code, id)
				values(?, ?)""", (code, script.id))

@common.transaction("texts")
def make_scripts_tables():
	db = common.db("texts")
	db.execute("delete from scripts_by_code")
	db.execute("delete from scripts_list")
	process_scripts(db, scripts_hierarchy, None)

@common.transaction("texts")
def main():
	f = sys.argv[1]
	t = tree.parse(f)

	assign_languages(t)

	def print_stuff(root):
		match root:
			case tree.Branch():
				print(root.assigned_lang, root.inferred_lang, root)
				for node in root:
					print_stuff(node)
			case _:
				print(root.assigned_lang, root.inferred_lang, repr(root))
	print_stuff(t)

if __name__ == "__main__":
	#main()
	#make_scripts_tables()
	@common.transaction("texts")
	def f():
		load_data()
	f()
