"""Stuff for dealing with languages and scripts.

On the TEI tree, we annotate all nodes with language information: language name,
script name.

where should we stick lang infos in the internal representation? should have at
least @lang and @script. add it to each element, so that we don't need stateful
processing for figuring out languages.

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

For ISO 639-3 (languages), the authority is https://iso639-3.sil.org.

For ISO 639-5 (language families), the authority is
https://www.loc.gov/standards/iso639-5/index.html.

For scripts, we have dharma-internal codes.
"""

import sys, re, copy
import requests # pip install requests
from dharma import common, texts, tree

def scripts_hierarchy_to_html() -> tree.Tag:
	"""Convert the script hierarchy to an HTML representation.

	We use the data present in the db instead of the data defined in this
	module to be sure we always use the same version of the data."""
	db = common.db("texts")
	row = db.execute("""select * from scripts_list
		where parent is null""").fetchone()
	assert row
	root = tree.Tag("ul")
	if not row:
		return root
	li = tree.Tag("li")
	root.append(li)
	stack = [(li, row)]
	while stack:
		node, row = stack.pop()
		node.append(row["name"])
		node.append(" [")
		span = tree.Tag("span", class_="monospace")
		span.append(row["id"])
		node.append(span)
		node.append("]")
		child_rows = db.execute("""select * from scripts_list
			where parent = ?""", (row["id"],)).fetchall()
		if child_rows:
			children = tree.Tag("ul")
			for child_row in child_rows:
				child = tree.Tag("li")
				children.append(child)
				stack.append((child, child_row))
			node.append(children)
	return root


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

	def __init__(self, language="eng", script="latin", is_source=False):
		self.language = language
		self.is_source = is_source
		self.script = script

	def __repr__(self):
		return f"LanguageInfo({self.language}, {self.script})"

	def _fields(self):
		return self.language, self.script

	def __eq__(self, other):
		return self._fields() == other._fields()

	def __hash__(self):
		return hash(self._fields())

	def __str__(self):
		return f"{self.language} {self.script}"

	def copy(self):
		import copy
		return copy.copy(self)

def should_bubble_up(root):
	langs = set()
	for child in root:
		match child:
			case tree.String():
				if child.isspace():
					continue
			case tree.Comment() | tree.Instruction():
				continue
			case tree.Tag("head"):
				continue
		langs.add(child.notes["inferred_lang"])
	if len(langs) == 1:
		return langs.pop()

def recurse(root):
	match root:
		case tree.Tree():
			root.notes["assigned_lang"] = LanguageInfo()
			for child in root:
				recurse(child)
		case tree.Tag():
			root.notes["assigned_lang"] = extract_language(root)
			for child in root:
				recurse(child)
			if (lang := should_bubble_up(root)):
				root.notes["assigned_lang"] = lang
		case _:
			root.notes["assigned_lang"] = root.parent.notes["assigned_lang"]
	root.notes["inferred_lang"] = root.notes["assigned_lang"]

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

def extract_language(node):
	if (lang := node.notes.get("assigned_lang")):
		return lang
	parent_lang = node.parent.notes["assigned_lang"]
	if node.name not in tei_language_sensitive:
		return parent_lang
	lang_id = node["lang"].split("-")[0]
	script_elems = node["rendition"].split()
	script_id = ""
	is_source = None
	for elem in script_elems:
		if elem.startswith("class:"):
			tmp = elem.removeprefix("class:")
			if tmp == "undetermined":
				tmp = ""
			script_id = tmp
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
		return parent_lang
	node_lang = parent_lang.copy()
	if lang_id:
		node_lang.language = lang_id
		node_lang.is_source = is_source
	if script_id:
		node_lang.script = script_id
	else:
		# If the parent has a source language and the child has a study
		# one, don't inherit the parent's script but reset it to
		# "study". Conversely, if the parent has a study language
		# language and the child a source one, reset the script to
		# "source".
		if parent_lang.is_source and not node_lang.is_source:
			node_lang.script = "study"
		if not parent_lang.is_source and node_lang.is_source:
			node_lang.script = "source"
	return node_lang

def assign_languages(t):
	"""For assigning languages, we follow the basic inheritance rule: if a
        tag does not have an @xml:lang, it is assigned the language assigned its
        parent. But there are exceptions:

        ¶ If the tag is "foreign", "lem" or "rdg" and does not have an
        @xml:lang, we assume it is in some source language (as per the guide)
        and assign it a generic language named "source" and a script named
        "source" as well. These represent any source language (per contrast with
        languages used in translations).

	Furthermore, we store two language values per node:

	¶ Assigned language. Assigned when traversing the tree top-down. This
        follows what people explicitly indicate for @xml:lang.
	"""
	for node in t.find(".//*[(name()='foreign' or name()='lem' or name()='rdg') and not @lang]"):
		node.notes["assigned_lang"] = LanguageInfo(language="source",
			script="source_other")
	recurse(t)

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


########################## Database construction ###############################

def update_db():
	update_langs()
	update_scripts()

def update_langs():
	db = common.db("texts")
	recs, index = load_langs()
	db.execute("delete from langs_by_code")
	db.execute("delete from langs_by_name")
	db.execute("delete from langs_list")
	for rec in recs:
		db.execute("""
			insert into langs_list(rid, id, name, inverted_name,
	     			iso, custom, dharma, parent)
			values(:rid, :id, :name, :inverted_name, :iso,
				:custom, :dharma, :parent)""", rec)
		db.execute("insert into langs_by_name(id, name) values(?, ?)",
			(rec["id"], common.normalize_text(rec["name"])))
	for code, rec in sorted(index.items()):
		db.execute("insert into langs_by_code(code, id) values(?, ?)", (code, rec["id"]))

def load_langs():
	tbl3 = fetch_tsv("https://iso639-3.sil.org/sites/iso639-3/files/downloads/iso-639-3.tab")
	tbl3_bis = fetch_tsv("https://iso639-3.sil.org/sites/iso639-3/files/downloads/iso-639-3_Name_Index.tab")
	tbl5 = fetch_tsv("http://id.loc.gov/vocabulary/iso639-5.tsv")
	tbl0 = fetch_tsv(texts.save("project-documentation", "DHARMA_languages.tsv"))
	recs = [
	{
		"id": "lang",
		"name": "Any Language",
		"inverted_name": "Any Language",
		"iso": None,
		"custom": True,
		"dharma": True,
		"parent": None,
	}, {
		"id": "source",
		"name": "Source Language",
		"inverted_name": "Source Language",
		"iso": None,
		"custom": True,
		"dharma": True,
		"parent": "lang",
	}, {
		"id": "study",
		"name": "Study Language",
		"inverted_name": "Study Language",
		"iso": None,
		"custom": True,
		"dharma": True,
		"parent": "lang",
	}]
	index = {}
	for rec in recs:
		add_to_index(rec["id"], index, rec)
	for row in tbl3:
		assert row["Id"]
		rec = {
			"id": row["Id"],
			"name": row["Ref_Name"],
			"iso": 3,
			"custom": False,
			"dharma": False,
			"parent": "source",
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
			"parent": "source",
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
			}
			recs.append(rec)
			add_to_index(rec["id"], index, rec)
		elif row["Print_Name"] != rec["name"] or row["Inverted_Name"] != rec["inverted_name"]:
			rec["name"] = row["Print_Name"]
			rec["inverted_name"] = row["Inverted_Name"]
			rec["custom"] = True
		rec["dharma"] = True
		rec["parent"] = row["type"] or "source"
	assert all("inverted_name" in rec for rec in recs)
	recs.sort(key=lambda rec: rec["id"])
	for rid, rec in enumerate(recs, 1):
		rec["rid"] = rid
	root = None
	for rec in recs:
		if rec["parent"] is None:
			assert root is None
			root = rec
			continue
		rec["parent"] = index[rec["parent"]]["rid"]
	return recs, index

def fetch_tsv(file):
	"""Fetch a TSV file from some given source. `file` can be: a
	`texts.File` object, an absolute file path like `/foo/bar.tsv`, or an
	URL like `https://foo.com/bar.tsv`. Returns a list of rows, where each
	row is a `dict` mapping field names to field values in the given row.
	We assume the first row contains field names.

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

def update_scripts():
	db = common.db("texts")
	db.execute("delete from scripts_by_code")
	db.execute("delete from scripts_list")
	insert_script(db, load_scripts())

def insert_script(db, script):
	db.execute("""
		insert into scripts_list(rid, id, name, inverted_name, parent)
		values(:rid, :id, :name, :inverted_name, :parent)""", script)
	for code in script["ids"]:
		db.execute("""insert into scripts_by_code(code, id)
			values(?, ?)""", (code, script["id"]))
	for child in script["children"]:
		insert_script(db, child)

def load_scripts():
	f = texts.File("project-documentation", "DHARMA_scripts.xml")
	common.db("texts").save_file(f)
	t = tree.parse_string(f.text)
	root = process_script_node(t.root)
	patch_scripts(root)
	make_hierarchy(root)
	return root

def process_script_node(script):
	rec = {}
	rec["ids"] = []
	for sid in script.find("id"):
		sid = sid.text()
		if not sid:
			continue
		common.append_unique(rec["ids"], sid)
	if len(rec["ids"]) < 1:
		raise Exception("bad value")
	rec["id"] = rec["ids"][0]
	name = script.first("name")
	if name:
		name = name.text()
	if not name:
		name = rec["ids"][0]
	rec["name"] = name
	inverted_name = script.first("inverted_name")
	if inverted_name:
		inverted_name = inverted_name.text()
	if not inverted_name:
		inverted_name = rec["name"]
	rec["inverted_name"] = inverted_name
	rec["children"] = []
	for child in script.find("script"):
		child = process_script_node(child)
		rec["children"].append(child)
	return rec

def patch_scripts(script):
	"""Add extra complement categories to the scripts hierarchy.

	In our TEI encoding, people have the option to use a non-leaf script
	category (like "arabic") or a leaf script category (like "jawi"). For
	search, we want all assigned scripts to be leaves. Thus, for the
	internal representation, we create complementary categories in such a
	way that all branches have a complementary leaf. For "arabic", we thus
	have two subcategories "jawi" and "arabic_other"; the latter is used
	when the user indicated "arabic", so that the identifier "arabic"
	remains available for search and does mean "anything in arabic, whether
	jawi or not".
	"""
	if not script["children"]:
		return
	compl = {
		"ids": [sid + "_other" for sid in script["ids"]],
		"name": script["name"] + " (other)",
		"inverted_name": script["inverted_name"] + " (other)",
		"children": [],
	}
	compl["id"] = compl["ids"][0]
	script["children"].append(compl)
	for child in script["children"]:
		patch_scripts(child)

def make_hierarchy(root, rid=0, parent=None):
	"Add record ids and pointers to parent records."
	rid += 1
	root["rid"] = rid
	root["parent"] = parent
	for child in root.get("children", []):
		rid = make_hierarchy(child, rid, root["rid"])
	return rid

if __name__ == "__main__":
	@common.transaction("texts")
	def f():
		update_db()
	f()
