# For parsing TEI files into Document objects

import os, sys, re, html, urllib.parse, logging, posixpath, copy
from dharma import prosody, people, tree, gaiji, common, biblio, langs, document

def XML(s):
	r = tree.parse_string(f"<root>{s}</root>")
	r.root.unwrap()
	return r

# Handlers are tested per order of appearance in this file, so the most
# specific ones should come first.
HANDLERS = []

def handler(path):
	def decorator(f):
		HANDLERS.append((tree.Node.match_func(path), f))
		return f
	return decorator

class Parser:

	def __init__(self, t):
		self.tree = t
		self.document = document.Document()
		self.document.tree = self.tree
		self.document.ident = os.path.basename(os.path.splitext(self.tree.file)[0])
		self.handlers = HANDLERS
		# Nodes in this set are ignored in dispatch(). These nodes
		# still remain in the tree and are still accessible from
		# within handlers.
		self.visited = set()
		#----- NEW stuff
		self.stack = []
		# Flag
		self.ignore_notes = False

	def push(self, node, **attrs):
		match node:
			case tree.Node():
				pass
			case str():
				node = tree.Tag(node, attrs)
			case _:
				raise Exception
		self.stack.append(node)
		return node

	def pop(self):
		return self.stack.pop()

	def join(self):
		self.append(self.pop())

	@property
	def top(self):
		return self.stack[-1]

	def start_span(self, klass=None, tip=None):
		span = tree.Tag("span")
		if klass:
			span["class"] = klass
		if tip:
			if isinstance(tip, tree.Node):
				tip = tip.xml()
			else:
				assert isinstance(tip, str)
			span["tip"] = html.escape(tip)
		self.push(span)

	def end_span(self):
		span = self.pop()
		assert span.name == "span"
		self.append(span)

	def append(self, node):
		self.top.append(node)

	def extend(self, nodes):
		for node in nodes:
			self.append(node)

	def add_text(self, text):
		self.top.append(str(text))

	def add_display(self, text):
		self.top.append(str(text)) # str() in case this is a tree.String

	def _get_bib_entry(self, short_title):
		external = False
		entry = self.document.bib_entries.get(short_title)
		if not entry:
			# It should occur in the global bibliography. We cache
			# the result to only perform a single database lookup.
			external = True
			entry = self.document.external_bib_entries.get(short_title)
			if not entry:
				entry = biblio.Entry(short_title)
				self.document.external_bib_entries[short_title] = entry
		return entry, external

	def bib_entry(self, short_title, loc=[], siglum=None):
		entry = self.document.bib_entries[short_title]
		return entry.xml(loc=loc, siglum=siglum)

	def bib_reference(self, short_title, rend="default", location=[], contents=[]):
		entry, external = self._get_bib_entry(short_title)
		ref = entry.reference(rend=rend, location=location,
			siglum=self.document.sigla.get(short_title),
			external_link=external,
			contents=contents)
		return ref

	def get_prosody_entry(self, name):
		entry = self.document._prosody_entries.get(name, object)
		if entry is object:
			db = common.db("texts")
			entry = db.execute(
				"""select pattern, description, entry_id
				from prosody where name = ?""",
				(name,)).fetchone() or None
			self.document._prosody_entries[name] = entry
		return entry

	def dispatch(self, node):
		if node in self.visited:
			return
		match node:
			case tree.Comment() | tree.Instruction():
				return
			case tree.String():
				# XXX rather do that on the final representation
				self.add_text(str(node).replace("'", "’"))
				return
			case tree.Tag():
				pass
			case _:
				assert 0, repr(node)
		for matcher, f in self.handlers:
			if matcher(node):
				break
		else:
			self.complain(node)
			self.add_text(node.text())
			return
		try:
			f(self, node)
		except tree.Error as e:
			self.complain(e)

	def dispatch_children(self, node, only_tags=False):
		for child in node:
			if only_tags and not isinstance(child, tree.Tag):
				continue
			self.dispatch(child)

	def complain(self, msg):
		print("UNKNOWN %s" % msg, file=sys.stderr)

# In the apparatus
@handler("lem")
def parse_lem(p, lem):
	p.dispatch_children(lem)
	add_lemmas_links(p, lem["source"])

"""
				XXX finish with this mess
the format of the contents doesn't depend directly on what the link points to:
* text id (put in monospace)
* url (in monospace)
* siglum (not monospace)
¶ if there is no @href, put the link in red

the bib link itself must be <a>contents</a>
but always wrap them inside a <span class="bib-reference"> to account for the citedRrange

for now the formatting of biblio references is in biblio.py, is it better if we
do everything in the present file? no, because the biblio entries formatting
MUST be done in the biblio module.
"""

def process_url(link):
	url = urllib.parse.urlparse(link)
	# The fancy prefixes we use like "bib" and "part" are private URI
	# schemes. See https://tei-c.org/release/doc/tei-p5-doc/en/html/SA.html#SAPU
	# However, we ignore what <listPrefixDef> says about the scheme.
	if url.scheme == "bib":
		return url.geturl()
	# Simplify the URL if it refers to something on our server:
	# http(s)?://(www\.)?dharmalekha.info/foo -> /foo
	if url.scheme in ("http", "https") and url.netloc in ("dharmalekha.info", "www.dharmalekha.info"):
		url = url._replace(scheme="", netloc="")
	if url.hostname:
		# It doesn't point to something on our server.
		return url.geturl()
	# We're dealing with a path ("foo", "/foo", etc.), thus something hosted
	# on our server. Make the path absolute and drop trailing slashes.
	# We have one of:
	# "foo" -> "/texts/foo"
	# "/foo" -> "/foo"
	# "/foo/" -> "/foo"
	path = url.path.rstrip("/") or "/"
	path = posixpath.join("/texts", path)
	# If this is a text, drop the file extension, thus
	# "/texts/DHARMA_INSIDENKTuhanyaru.xml" -> "/texts/DHARMA_INSIDENKTuhanyaru"
	# And also remove the "DHARMA_" prefix:
	# "/texts/DHARMA_INSIDENKTuhanyaru" -> "/texts/INSIDENKTuhanyaru"
	if path.startswith("/texts/"):
		name = posixpath.basename(path)
		name = posixpath.splitext(name)[0]
		name = name.removeprefix("DHARMA_")
		path = posixpath.join(posixpath.dirname(path), name)
	url = url._replace(path=path)
	return url.geturl()

bibl_units = set(biblio.cited_range_units)

def extract_bib_ref(node):
	assert node.name == "bibl"
	ptr = node.first("ptr")
	if not ptr:
		return None, None
	target = ptr["target"]
	if target == "bib:AuthorYear_01":
		return None, None
	ref = target.removeprefix("bib:")
	loc = []
	for r in node.find("citedRange"):
		unit = r["unit"] or "page"
		if unit not in bibl_units:
			unit = "mixed"
		val = r.text()
		if not val:
			continue
		loc.append((unit, val))
	return ref, loc

# For printing entries within the bibliography. In this context, bibl needs to
# be replaced with the bibliography entry.
@handler("listBibl/bibl")
def parse_listbibl_bibl(p, bibl):
	short_title, loc = extract_bib_ref(bibl)
	if not short_title:
		return # XXX use a dummy entry
	siglum = p.sigla.get(short_title)
	p.append(p.bib_entry(short_title, loc=loc, siglum=siglum))

bibl_rend_formats = {"default", "omitname", "ibid", "siglum"}

@handler("bibl[ptr]")
@handler("bibl[ref]")
def parse_bibl_ref(p, bibl):
	rend = bibl["rend"]
	if rend not in bibl_rend_formats:
		rend = "default"
		assert rend in bibl_rend_formats
	ref = bibl.first("ptr") or bibl.first("ref")
	# The ptr/@target is supposed to start with "bib:". If it doesn't, we
	# still assume it refers to a bibliography entry.
	short_title = ref["target"].removeprefix("bib:")
	location = []
	for r in bibl.find("citedRange"):
		unit = r["unit"] or "page"
		if unit not in bibl_units:
			unit = "mixed"
		value = r.text()
		if not value:
			continue
		location.append((unit, value))
	p.append(p.bib_reference(short_title, rend=rend, contents=ref, location=location))
	# XXX move this comment Use short title when we have bibl/ptr with a bib pointer, in all other
	# cases use the siglum with author+date in tooltip (or author+date if there is no siglum; or whatever the
	# contents of the point is if it is not empty).

@handler("bibl")
def parse_bibl(p, bibl):
	p.start_span(klass="bib-ref")
	p.dispatch_children(bibl)
	p.end_span()

# The syntax for ref is <ref target="myurl">foo</ref>, equivalent to the HTML
# <a href="myurl">foo</ref>. <ptr/> is like <ref> except that it is supposed
# to be empty. Even so, we try to deal appropriately with a non-empty <ptr/>.
@handler("ref[@target and not empty()]")
@handler("ptr[@target and not empty()]")
def parse_ref(p, ref):
	assert ref["target"] and not ref.empty
	url = process_url(ref["target"])
	klass = "url"
	if url.startswith("/texts/"):
		klass += " text-id"
	p.push(tree.Tag("a", {"href": url, "class": klass}))
	p.dispatch_children(ref)
	p.join()

@handler("ref[@target]") # ref[@target and empty()]
@handler("ptr[@target]") # ptr[@target and empty()]
def parse_ref_empty(p, ref):
	assert ref["target"] and ref.empty
	url = process_url(ref["target"])
	klass = "url"
	if url.startswith("/texts/"):
		klass += " text-id"
	p.push(tree.Tag("a", {"href": url, "class": klass}))
	p.add_text(url.removeprefix("/texts/"))
	p.join()

@handler("ref") # ref[not @target]
@handler("ptr") # ptr[not @target]
def parse_other_ref(p, ref):
	assert not ref["target"]
	p.dispatch_children(ref)

def add_lemmas_links(p, sources):
	for ref in sources.split():
		ref = ref.removeprefix("bib:")
		if not ref:
			continue
		p.add_text(" ")
		p.add_bib_ref(ref, siglum=True)

@handler("rdg")
def parse_rdg(p, rdg):
	p.start_span(klass="reading", tip="Reading")
	p.dispatch_children(rdg)
	p.end_span()
	add_lemmas_links(p, rdg["source"])

@handler("app")
def parse_app(p, app):
	loc = app["loc"] or "?"
	p.add_html(document.format_lb(n=loc))
	p.add_text(" ")
	lem = app.first("lem")
	if lem:
		p.dispatch(lem)
	rdgs = app.find("rdg")
	if rdgs:
		p.add_text(" \N{white medium diamond} ")
	notes = app.find("note") # we deal with other notes elsewhere
	for i, rdg in enumerate(rdgs):
		p.dispatch(rdg)
		if i < len(rdgs) - 1:
			p.add_text("; ")
		elif not notes:
			p.add_text(".")
	for note in notes:
		p.add_text(" • ")
		p.dispatch_children(note)

@handler("listApp")
def parse_listApp(p, listApp):
	apps = listApp.find("app[lem[not empty()]]")
	if not apps:
		return
	prev_loc = None
	for app in apps:
		if prev_loc == app["loc"]:
			p.add_text(" \N{EM DASH} ")
		else:
			if prev_loc is not None:
				p.add_log(">para")
			p.add_log("<para")
		p.dispatch(app)
		prev_loc = app["loc"]
	p.add_log(">para")

@handler("num")
def parse_num(p, num):
	if num["value"] and num["value"] == num.text() and not num["cert"] == "low":
		tip = "" # Pointless to add a tooltip in this case.
	elif num["value"]:
		tip = f"Numeral {num['value']}"
	elif num["atLeast"] and num["atMost"]:
		tip = f"Numeral between {num['atLeast']} and {num['atMost']} inclusive"
	elif num["atLeast"]:
		tip = f"Numeral greater than or equal to {num['atLeast']}"
	elif num["atMost"]:
		tip = f"Numeral smaller than or equal to {num['atMost']}"
	elif num.text().isdigit() and not num["cert"] == "low":
		tip = "" # Pointless to add a tooltip in this case.
	else:
		tip = "Numeral"
	if num["cert"] == "low":
		tip += " (low certainty)"
	p.push(tree.Tag("span", class_="num", tip=tip or None))
	p.dispatch_children(num)
	p.join()

# < editorial

# Try to have more precise tooltips for this. If this does not work, we fall
# back to a generic one.
@handler("supplied[@reason='subaudible']")
def parse_supplied_subaudible(p, supplied):
	if not supplied.assigned_lang.is_source:
		tip = "Text added to the translation for the sake of target language syntax"
		return emit_supplied(p, supplied, tip, "[]")
	match supplied.text():
		case "'" | "’":
			tip = XML("<i>Avagraha</i> added by the editor to clarify the interpretation")
		case ".":
			tip = "Punctuation added by the editor at semantic break"
		case _:
			tip = "Editorial addition to clarify interpretation"
	return emit_supplied(p, supplied, tip, "⟨⟩")

# EGD "Additions to the translation"
# EGD "Marking up restored text"
# EGD "The basis of restoration"
supplied_tbl = {
	# EGD: "words added to the translation for the sake of target language
	# syntax"
	# subaudible is handled separately
	# EGD: "words implied by the context and added to the translation for
	# the sake of clarification or disambiguation"
	"explanation": ("()", "Text inserted into the translation as explanation or disambiguation"),
	# EGD: "lost" and "omitted" indicate "segments of translation corresponding
	# to text restored by the editor in the original" (they are used both
	# in the edition and in the translation)
	"lost": ("[]", "Lost text"),
	"omitted": ("⟨⟩", "Omitted text"),
	# EGD under "Marking up restored text" says that "undefined" is used when it's not possible
	# to tell whether we have "lost" or "omitted"
	"undefined": ("[]", "Text supplied for undefined reason (lost or omitted)")
}
# OK
@handler("supplied") # [not @reason='subaudible']
def parse_supplied(p, supplied):
	brackets, tip = supplied_tbl.get(supplied["reason"], supplied_tbl["lost"])
	return emit_supplied(p, supplied, tip, brackets)

def emit_supplied(p, supplied, tip, brackets):
	ldelim, rdelim = brackets
	p.push(tree.Tree())
	# XXX must omit <note> in all cases where we construct a tooltip
	p.append(copy.copy(tip))
	if supplied["cert"] == "low":
		p.append(" (low certainty)")
	match supplied["evidence"]:
		case "parallel":
			p.append("; restoration based on parallel")
		case "previouseditor":
			p.append("; restoration based on previous edition (not assessable)")
	tip = p.pop().xml()
	p.push(tree.Tag("span", class_="supplied", tip=tip))
	p.add_display(ldelim)
	p.dispatch_children(supplied)
	if supplied["cert"] == "low":
		p.add_display("?")
	p.add_display(rdelim)
	p.join()

# § Premodern insertion
add_place_tbl = {
	"inline": "Scribal addition within the same line or in the immediate vicinity of the locus",
	"below": "Scribal addition below the line",
	"above": "Scribal addition above the line",
	"top": "Scribal addition in the top margin",
	"bottom": "Scribal addition in the bottom margin",
	"left": "Scribal addition in the left margin",
	"right": "Scribal addition in the right margin",
	"overstrike": "Scribal addition made in the space where a previous string of text has been erased",
	"unspecified": "Scribal addition: no location information available",
}
@handler("add")
def parse_add(p, node, deleted=None):
	p.push(tree.Tree())
	tip = add_place_tbl.get(node["place"], add_place_tbl["unspecified"])
	p.append(tip)
	if deleted:
		p.append(" (overwritten text: ")
		p.push(tree.Tag("span", class_="del"))
		p.append("⟦")
		p.dispatch_children(deleted)
		p.append("⟧")
		p.join()
		p.append(")")
	tip = p.pop().xml()
	p.push(tree.Tag("span", class_="add", tip=tip))
	p.add_display("⟨⟨")
	p.dispatch_children(node)
	p.add_display("⟩⟩")
	p.join()

# § Premodern deletion
del_rend_tbl = {
	"strikeout": "Scribal deletion: text struck through or cross-hatched",
	"ui": XML("Scribal deletion: combined application of vowel markers <i>u</i> and <i>i</i> to characters to be deleted"),
	"other": "Scribal deletion",
	"corrected": "Scribal deletion: corrected text",
}
@handler("del")
def parse_del(p, node, added=None):
	p.push(tree.Tree())
	tip = del_rend_tbl.get(node["rend"], del_rend_tbl["other"])
	p.append(copy.copy(tip))
	if added:
		p.append(" (replacement text: ")
		p.push(tree.Tag("span", class_="add"))
		p.add_text("⟨⟨")
		p.dispatch_children(added)
		p.add_text("⟩⟩")
		p.join()
		p.append(")")
	tip = p.pop().xml()
	p.push(tree.Tag("span", class_="del", tip=tip))
	p.add_display("⟦")
	p.dispatch_children(node)
	p.add_display("⟧")
	p.join()

# § Premodern correction
@handler("subst")
def parse_subst(p, subst):
	# For search, should just keep the text of <add>
	add = subst.first("add")
	dele = subst.first("del")
	if not add or not dele:
		return p.dispatch_children(subst)
	parse_del(p, dele, add)
	parse_add(p, add, dele)

def text_to_html(p, mark):
	block = p.top
	while mark < len(block.code):
		t, data, params = block.code[mark]
		if t == "text":
			params.setdefault("plain", False)
			params.setdefault("logical", True)
			params.setdefault("physical", True)
			block.code[mark] = ("html", html.escape(data), params)
		mark += 1

@handler("sic")
def parse_sic(p, sic, corr=None):
	p.push(tree.Tree())
	p.append("Incorrect text")
	if corr:
		class_ = "sic"
		p.append(" (emendation: ")
		p.push(tree.Tag("span", class_="corr"))
		p.add_text("⟨")
		p.dispatch_children(corr)
		p.add_text("⟩")
		p.join()
		p.add_text(")")
	else:
		class_ = "sic standalone"
	p.push(tree.Tag("span", class_=class_, tip=p.pop().xml()))
	p.add_text("¿")
	p.dispatch_children(sic)
	p.add_text("?")
	p.join()

@handler("corr")
def parse_corr(p, corr, sic=None):
	p.push(tree.Tree())
	p.append("Emended text")
	if sic:
		class_ = "corr"
		p.append(" (original: ")
		p.push(tree.Tag("span", class_="sic"))
		p.add_text("¿")
		p.dispatch_children(sic)
		p.add_text("?")
		p.join()
		p.add_text(")")
	else:
		class_ = "corr standalone"
	p.push(tree.Tag("span", class_=class_, tip=p.pop().xml()))
	p.add_text('⟨')
	p.dispatch_children(corr)
	p.add_text('⟩')
	p.join()

@handler("orig")
def parse_orig(p, orig, reg=None):
	p.push(tree.Tree())
	p.append("Non-standard text")
	if reg:
		class_ = "orig"
		p.append(" (standardisation: ")
		p.push(tree.Tag("span", class_="reg"))
		p.add_text("⟨")
		p.dispatch_children(reg)
		p.add_text("⟩")
		p.join()
		p.add_text(")")

	else:
		class_ = "orig standalone"
	p.push(tree.Tag("span", class_=class_, tip=p.pop().xml()))
	p.add_text("¡")
	p.dispatch_children(orig)
	p.add_text("!")
	p.join()

@handler("reg")
def parse_reg(p, reg, orig=None):
	p.push(tree.Tree())
	p.append("Standardised text")
	if orig:
		class_ = "reg"
		p.append(" (original: ")
		p.push(tree.Tag("span", class_="orig"))
		p.add_text("¡")
		p.dispatch_children(orig)
		p.add_text("!")
		p.join()
		p.add_text(")")
	else:
		class_ = "reg standalone"
	p.push(tree.Tag("span", class_=class_, tip=p.pop().xml()))
	p.add_text("⟨")
	p.dispatch_children(reg)
	p.add_text("⟩")
	p.join()

@handler("unclear")
def parse_unclear(p, node, standalone=True):
	p.push(tree.Tree())
	if node["cert"] == "low":
		p.append("Tentative reading")
	else:
		p.append("Unclear text")
	if node["reason"] == "eccentric_ductus":
		p.append(" (")
		p.push(tree.Tag("i"))
		p.append("eccentric_ductus")
		p.join()
		p.append(")")
	p.push(tree.Tag("span", class_="unclear", tip=p.pop().xml()))
	if standalone:
		p.append("(")
	p.dispatch_children(node)
	if node["cert"] == "low":
		p.append("?")
	if standalone:
		p.append(")")
	p.join()

# We expect one of:
#
# <choice>(<unclear>...</unclear>)+</choice>
# <choice><sic>...</sic><corr>...</corr></choice>
# <choice><orig>...</orig><reg>...</reg></choice>
#
# In case #1, for search and plain should just keep the text of the 1st unclear.
# For #2 and #3, for searching should keep <corr> and <reg>, ignore the rest.
@handler("choice")
def parse_choice(p, node):
	children = node.find("*")
	if all(child.name == "unclear" for child in children):
		p.push(tree.Tag("span", tip="Unclear (several possible readings)"))
		p.append("(")
		for i, child in enumerate(children):
			p.dispatch_children(child)
			if i < len(children) - 1:
				p.append("/")
		p.append(")")
		p.join()
	elif len(children) != 2:
		p.dispatch_children(node)
	elif (sic := node.first("sic")) and (corr := node.first("corr")):
		parse_sic(p, sic, corr)
		parse_corr(p, corr, sic)
	elif (orig := node.first("orig")) and (reg := node.first("reg")):
		parse_orig(p, orig, reg)
		parse_reg(p, reg, orig)
	else:
		p.dispatch_children(node)

# EGD "Editorial deletion (suppression)"
@handler("surplus")
def parse_surplus(p, node):
	p.push(tree.Tag("span", class_="surplus", tip="Superfluous text erroneously added by the scribe"))
	p.append("{")
	p.dispatch_children(node)
	p.append("}")
	p.join()

# > editorial

# For <note> elements anywhere but in the apparatus, where <note> has a peculiar
# purpose.
@handler("note")
def parse_note(p, note):
	if p.ignore_notes:
		return
	out = p.push(tree.Tag("note"))
	p.ignore_notes = True
	if (resps := note["resp"]):
		append_names(p, resps.split())
		p.add_text(": ")
	elif (refs := note["source"]):
		append_sources(p, refs.split())
		p.add_text(": ")
	p.dispatch_children(note)
	p.ignore_notes = False
	p.join()
	p.document.notes.append(out)

# Put <foreign> in italics.
@handler("foreign")
def parse_foreign(p, foreign):
	p.push(tree.Tag("i"))
	p.dispatch_children(foreign)
	p.join()

# < milestones

"""
what shall we do


LOGICAL
elif data.startswith("=") and params["type"] == "pagelike":
	unit = html.escape(data[1:].title())
	text = f"⟨{unit} {params['n']}"
	if params["label"]:
		text += f": {params['label']}"
	text += "⟩"
	buf.append('<span class="pagelike" data-tip="%s start">%s</span>' % (unit, html.escape(text)))
elif data.startswith("=") and params["type"] == "gridlike":
	unit = html.escape(data[1:].title())
	text = f"⟨{unit} {params['n']}"
	if params["label"]:
		text += f": {params['label']}"
	text += "⟩"
	buf.append('<span class="gridlike" data-tip="%s start">%s</span>' % (unit, html.escape(text)))
else:

PHYSICAL
elif data.startswith("=") and params["type"] == "pagelike":
	unit = html.escape(data[1:].title())
	text = f"{unit} {params['n']}"
	if params["label"]:
		text += f": {params['label']}"
	buf.append('<div class="pagelike"><span data-tip="%s start">%s</span></div>' % (unit, html.escape(text)))
elif data.startswith("=") and params["type"] == "gridlike":
	unit = html.escape(data[1:].title())
	text = f"⟨{unit} {params['n']}"
	if params["label"]:
		text += f": {params['label']}"
	text += "⟩"
	buf.append('<span class="gridlike" data-tip="%s start">%s</span>' % (unit, html.escape(text)))
else:
"""

def get_n(node):
	n = node["n"]
	if not n:
		return ""
	n = n.replace("_", " ").replace("-", "\N{en dash}")
	return n

def milestone_break(node):
	return common.to_boolean(node["break"], True)

def from_boolean(obj):
	if obj is True:
		return "true"
	assert obj is False
	return "false"

def append_milestone_label(p, node):
	p.push(tree.Tag("span"))
	# On alignment, EGD § "Alignment"
	if (style := node["style"]) and (m := re.fullmatch(r"text-align:\s?(right|center|left|justify);?", style)):
		align = m.group(1)
	else:
		# If not given, we assume it is not important and omit the
		# alignment from the tooltip.
		align = None
	unit = (node["unit"] or "column").title()
	p.append("⟨")
	p.append(unit)
	if (n := get_n(node)):
		p.append(" ")
		p.append(n)
	if (label := node.first("stuck-following-sibling::label")):
		p.append(": ")
		p.dispatch_children(label)
		p.visited.add(label)
	p.append("⟩")
	p.join()

@handler("milestone")
def parse_milestone(p, node):
	break_ = milestone_break(node)
	match node["type"]:
		case "pagelike":
			type = "page"
		case "gridlike" | _:
			type = "cell"
	p.push(tree.Tag(type, break_=from_boolean(break_)))
	append_milestone_label(p, node)
	p.join()

"""

def format_lb(n=None, brk=None, align=None):
	assert n
	n = html.escape(n)
	if align:
		tip = f'{alignments[align]} line start'
	else:
		tip = "Line start"
	tip = html.escape(tip)
	return f'<span class="lb" data-tip="{tip}">⟨{n}⟩</span>'

"""
@handler("lb")
def parse_lb(p, node):
	break_ = milestone_break(node)
	p.push(tree.Tag("line", break_=from_boolean(break_)))
	append_milestone_label(p, node)
	p.join()

fw_places = {
	"bot-left": "bottom left",
	"bot-right": "bottom right",
	"bottom": "bottom",
	"left": "left",
	"right": "right",
	"top": "top",
	"top-left": "top left",
	"top-right": "top right",
}
# TODO the guide does not talk about using <fw> about other page-like, but
# we should allow this anyway.
@handler("pb")
def parse_pb(p, node):
	n = get_n(node)
	brk = milestone_break(node)
	p.push(tree.Tag("page", unit="page", n=n, break_=from_boolean(brk)))
	append_milestone_label(p, node)
	p.join()
	"""
	fws = []
	while True:
		fw = elem.stuck_following_sibling()
		if not fw or not fw.name == "fw":
			break
		fws.append(fw)
		elem = fw
	# XXX should mark fws as visited, so that a misplaced fw is
	# still displayed by parse_fw. idem for <head> and such.
	# and should also mark text nodes in-between!
	if fws:
		for i, fw in enumerate(fws):
			p.start_span(klass="fw", tip="Foliation")
			place = fw["place"]
			if not place:
				place = "top"
			elif place in fw_places:
				place = fw_places[place]
			else:
				# keep the given value, even though it's wrong
				pass
			p.add_html("⟨", logical=True, physical=False, full=True)
			p.add_text(f"{place}: ")
			p.start_span(klass="fw-contents")
			p.dispatch_children(fw)
			p.end_span()
			p.add_html("⟩", logical=True, physical=False, full=True)
			p.end_span()
			if i < len(fws) - 1:
				p.add_html(" ", logical=False, physical=True, full=False)
	p.add_phys("}page")
	"""

# > milestones

# Valid cases are:
#	<space [type="semantic"]/> (shorthand is '_')
#	<space [type="semantic"] quantity=... unit="character"/>
#	<space type="vacat" quantity=... unit="character"/>
#	<space type="(binding-hole|descender|ascender|defect|feature)"/>
#	<space type="unclassified"/>
#	<space type="unclassified" quantity=... unit="character"/>
space_types = {
	"semantic": {
		"text": "_",
		"tip": "semantic space",
	},
	"binding-hole": {
		"text": "◯",
		"tip": "binding hole",
	},
	"descender": {
		"text": "⊔",
		"tip": "space left blank in a line because (part of) another character hanging down from the previous line encroaches on the current line",
	},
	"ascender": {
		"text": "⊓",
		"tip": "space left blank in a line because (part of) another (pre-conceived) character popping up from the following line encroaches on the current line",
	},
	"defect": {
		"text": "□",
		"tip": "space; the writing skips a blemish of the surface that was not deliberately created (such as a natural crack or pit, or a fault in the creation of the writing surface)",
	},
	"feature": {
		"text": "_",
		"tip": "space; the writing skips a deliberately created feature (other than binding holes, ascenders and descenders) on the surface (such as engraved artwork, high relief, or a seal attached directly to a copper plate)",
	},
	"vacat": {
		"text": "_",
		"tip": "vacat space; the area was left blank when the rest of the inscription was engraved, possibly with the intent to be filled later on",
	},
	"unclassified": {
		"text": "_",
		"tip": "significant space that does not fit other categories",
	}
}
@handler("space")
def parse_space(p, space):
	type = space["type"]
	if type not in space_types:
		type = "semantic"
	if type in ("semantic", "vacat", "unclassified"):
		quant = space["quantity"]
		if not quant.isdigit():
			quant = "1"
		quant = int(quant)
		if quant < 1:
			quant = 1
		unit = space["unit"]
		if unit != "character":
			unit = "character"
	info = space_types[type]
	tip = info["tip"]
	text = info["text"]
	if type in ("semantic", "vacat", "unclassified"):
		if quant < 2:
			tip = f"small {type} space (from barely noticeable to less than two average character widths in extent)"
		else:
			tip = f"large {type} space (about {quant} {unit}s wide)"
		text *= quant
	p.push(tree.Tag("span", class_="space", tip=common.sentence_case(tip)))
	p.add_text(text) # XXX must only be made visible in physical and full, not in logical
	p.join()

# <abbreviations

@handler("abbr")
def parse_abbr(p, node):
	p.push(tree.Tag("span", class_="abbr", tip="Abbreviated text"))
	p.dispatch_children(node)
	p.join()

@handler("ex")
def parse_ex(p, node):
	if node["cert"] == "low":
		tip = "Abbreviation expansion (uncertain)"
	else:
		tip = "Abbreviation expansion"
	p.push(tree.Tag("span", class_="abbr-expansion", tip=tip))
	p.append("(")
	p.dispatch_children(node)
	p.append(")")
	p.join()

@handler("am")
def parse_am(p, am):
	p.push(tree.Tag("span", class_="abbr-mark", tip="Abbreviation mark"))
	p.dispatch_children(am)
	p.join()

# We expect:
#	<expan>((<abbr>(text|<am>...</am>)</abbr>)|(<ex>...</ex>))+</expan>
# This is not good (can't deal with <note>, etc.). Need to straighten this out.
@handler("expan")
def parse_expan(p, node):
	def iter_abbr_without_am(cur):
		match cur:
			case tree.Tag(name="am"):
				pass
			case tree.Tag():
				for child in cur:
					yield from iter_abbr_without_am(child)
			case tree.String():
				yield cur
	p.push(tree.Tree())
	p.append("Abbreviation (contracted form: ")
	p.push(tree.Tag("span", class_="abbr-contracted"))
	for abbr in node.find("abbr"):
		p.append(abbr.text())
	p.join()
	p.append("; expanded form: ")
	p.push(tree.Tag("span", class_="abbr-expanded"))
	for child in node.find("*[name() = 'abbr' or name() = 'ex']"):
		if child.name == "ex":
			p.append(child.text())
			continue
		for s in iter_abbr_without_am(child):
			p.append(s.copy())
	p.join()
	p.append(")")
	p.push(tree.Tag("span", class_="abbr-full", tip=p.pop().xml()))
	p.dispatch_children(node)
	p.join()

# >abbreviations

# XXX not refactored
# XXX @rend="check" should be handled everywhere but is not

# There is @type=aksara|component which we are not dealing with but that is
# apparently useless.
@handler("seg[not stuck-child::gap]")
def parse_seg(p, seg):
	rend = seg["rend"].split()
	if "pun" in rend:
		p.push(tree.Tag("span", class_="pun", tip=XML("Pun (<i>ślesa</i>").xml()))
		p.append("{")
	if "check" in rend:
		p.push(tree.Tag("span", class_="check", tip="To check"))
	if seg["cert"] == "low":
		p.push(tree.Tag("span", tip="Uncertain segment"))
		p.append("¿")
	p.dispatch_children(seg)
	if seg["cert"] == "low":
		p.append("?")
		p.join()
	if "check" in rend:
		p.join()
	if "pun" in rend:
		p.append("}")
		p.join()

# XXX not general enough
@handler("div[@type='translation']//gap[@reason='ellipsis']")
def handle_gap_ellipsis(p, gap):
	p.start_span(tip="Untranslated segment")
	p.add_html("\N{horizontal ellipsis}", plain=True)
	p.end_span()

# XXX not refactored
# "component" is for character components like vowel markers, etc.; "character" is for akṣaras
# EGD: The EpiDoc element <gap/> ff (full section 5.4)
# EGD: "Scribal Omission without Editorial Restoration"
@handler("gap")
def parse_gap(p, gap):
	reason = gap["reason"] or "undefined" # most generic choice
	quantity = gap["quantity"]
	precision = gap["precision"]
	unit = gap["unit"] or "character"
	if reason == "ellipsis":
		p.add_html("\N{horizontal ellipsis}", plain=True)
		return
	if reason == "undefined":
		reason = "lost or illegible"
	child = gap.first("certainty")
	if child and child["match"] == ".." and child["locus"] == "name":
		reason = "possibly %s" % reason
	if unit == "component":
		unit = "character component"
	phys_repl = None
	if quantity.isdigit():
		quantity = int(quantity)
		repl = "["
		if precision == "low":
			repl += "ca. "
		if unit == "character":
			if reason == "lost":
				repl += f"{quantity}+"
			elif reason == "illegible":
				repl += f"{quantity}×"
			else:
				# reason = "undefined" (lost or illegible)
				repl += f"{quantity}*"
		elif unit == "character component":
			repl += quantity * "."
		else:
			repl += "%d %s %s" % (quantity, reason, common.numberize(unit, quantity))
		repl += "]"
		phys_repl = "["
		if precision == "low" and unit != "character":
			phys_repl += "ca. "
		if unit == "character":
			phys_repl += quantity * "*"
		elif unit == "character component":
			phys_repl += quantity * "."
		else:
			phys_repl += "%d %s %s" % (quantity, reason, common.numberize(unit, quantity))
		phys_repl += "]"
		tip = ""
		if precision == "low":
			tip += "About "
		tip += "%d %s %s" % (quantity, reason, common.numberize(unit, quantity))
	else:
		if unit == "character":
			repl = "[…]"
		else:
			repl = "[unknown number of %s %s]" % (reason, common.numberize(unit, +333))
		tip = "Unknown number of %s %s" % (reason, common.numberize(unit, +333))
	# <seg met="+++-++"><gap reason="lost" quantity="6" unit="character">
	# In this case, keep the tooltip, but display the meter instead of ****, etc.
	parent = gap.parent
	if isinstance(parent, tree.Tag) and parent.name == "seg" and parent["met"]:
		met = parent["met"]
		if prosody.is_pattern(met):
			met = prosody.render_pattern(met)
		else:
			met = html.escape(met)
		repl = f'[{met}]'
		phys_repl = None
	else:
		repl = html.escape(repl)
		if phys_repl is not None:
			phys_repl = html.escape(phys_repl)
	p.start_span(klass="gap", tip=tip)
	if phys_repl is not None and phys_repl != repl:
		p.add_html(repl, plain=True, physical=False)
		p.add_html(phys_repl, plain=True, logical=False, full=False)
	else:
		p.add_html(repl, plain=True)
	p.end_span()

# See mkfractiontable.py.
composed_fractions = {
	(0, 3): "\N{vulgar fraction zero thirds}",
	(1, 2): "\N{vulgar fraction one half}",
	(1, 3): "\N{vulgar fraction one third}",
	(1, 4): "\N{vulgar fraction one quarter}",
	(1, 5): "\N{vulgar fraction one fifth}",
	(1, 6): "\N{vulgar fraction one sixth}",
	(1, 7): "\N{vulgar fraction one seventh}",
	(1, 8): "\N{vulgar fraction one eighth}",
	(1, 9): "\N{vulgar fraction one ninth}",
	(2, 3): "\N{vulgar fraction two thirds}",
	(2, 5): "\N{vulgar fraction two fifths}",
	(3, 4): "\N{vulgar fraction three quarters}",
	(3, 5): "\N{vulgar fraction three fifths}",
	(3, 8): "\N{vulgar fraction three eighths}",
	(4, 5): "\N{vulgar fraction four fifths}",
	(5, 6): "\N{vulgar fraction five sixths}",
	(5, 8): "\N{vulgar fraction five eighths}",
	(7, 8): "\N{vulgar fraction seven eighths}",
}
# We try to use a uniform representation for fractions. If there is a
# precomposed code point for the given fraction, we use it, otherwise we use
# <sup>9</sup> + fraction slash + <sub>8</sub>.
@handler("g[@type='numeral']")
def parse_g_numeral(p, node):
	p.push(tree.Tag("numeral"))
	frac = re.match("([0-9]+)[/\N{fraction slash}]([0-9]+)", node.text())
	if frac:
		num, den = int(frac.group(1)), int(frac.group(2))
		composed = composed_fractions.get((num, den))
		if composed:
			p.append(composed)
		else:
			sup = tree.Tag("sup")
			sup.append(str(num))
			p.append(sup)
			p.append("\N{fraction slash}")
			sub = tree.Tag("sub")
			sub.append(str(den))
			p.append(sub)
	else:
		p.dispatch_children(node)
	p.join()

# g[not @type='numeral']
@handler("g")
def parse_g(p, node):
	# <g type="...">\.</g> for punctuation marks
	# <g type="...">§+</g> for space fillers
	# <g type="..."></g> in the other cases viz. for symbols whose function
	# is unclear.
	text = node.text()
	info = gaiji.get(node["type"])
	if text == ".":
		tip = f"Punctuation symbol: {info['description']}"
	elif re.fullmatch("§+", text):
		tip = f"Space-filler symbol: {info['description']}"
	else:
		tip = f"Symbol: {info['description']}"
	sym = tree.Tag("symbol", tip=tip)
	if info["text"]:
		sym["class"] = "symbol"
		sym.append(info["text"])
	else:
		sym["class"] = "symbol-placeholder"
		sym.append(f"<{info['name']}>")
	p.append(sym)

# XXX This doesn't always work, because we have intervening <lb/>, etc. within
# <hi>, so we need to split the <hi> into several elements. Needs to be done
# after building the output tree.
hi_table = {
	"italic": tree.Tag("i"),
	"bold": tree.Tag("b"),
	"superscript": tree.Tag("sup"),
	"subscript": tree.Tag("sub"),
	"check": tree.Tag("span", class_="check"),
	"grantha": tree.Tag("span", class_="grantha", tip="Grantha text"),
}
@handler("hi")
def parse_hi(p, hi):
	n = 0
	for rend in common.unique(hi["rend"].split()):
		node = hi_table.get(rend)
		if node:
			p.push(node.copy())
			n += 1
	p.dispatch_children(hi)
	for _ in range(n):
		p.join()

# < para-like

roman_table = [
	("M", 1000),
	("CM", 900),
	("D", 500),
	("CD", 400),
	("C", 100),
	("XC", 90),
	("L", 50),
	("XL", 40),
	("X", 10),
	("IX", 9),
	("V", 5),
	("IV", 4),
	("I", 1),
]
def to_roman(x):
	# Limited to 0...3999
	if x <= 0 or x >= 4000:
		return str(x)
	buf = ""
	for roman, arabic in roman_table:
		while x >= arabic:
			buf += roman
			x -= arabic
	return buf

def make_meter_heading(p, met):
	if not met:
		return
	if prosody.is_pattern(met):
		return prosody.render_pattern(met)
	entry = p.get_prosody_entry(met)
	if not entry:
		ret = tree.Tag("span")
		ret.append(met)
		return ret
	pattern, description, entry_id = entry
	name = common.sentence_case(met)
	value = pattern or description or "No metre description available"
	p.push(tree.Tag("a", href=f"/prosody#prosody-{entry_id}"))
	p.push(tree.Tag("span", tip=value))
	p.append(name)
	p.join()
	return p.pop()

# The guide does not talk about ab[@rend='stanza'], but still try to process it
# if it appears in an edition.
@handler("lg")
@handler("p[@rend='stanza']")
@handler("ab[@rend='stanza']")
def parse_lg(p, lg):
	numbered = from_boolean(len(lg.find("l")) > 4)
	p.push(tree.Tag("verse", numbered=numbered))
	# Generally we have a single number e.g. "10", but sometimes ranges
	# e.g. "10-20" (with various types of dashes). Try to do the most
	# generic thing viz. replace sequences of digits with the corresponding
	# Roman number whenever possible.
	n = re.sub(r"[0-9]+", lambda m: to_roman(int(m.group())), get_n(lg))
	met = make_meter_heading(p, lg["met"])
	if n or met:
		p.push(tree.Tag("head"))
		if n and met:
			p.append(n)
			p.append(". ")
			p.append(met)
		elif n:
			p.append(n)
		else:
			assert met
			p.append(met)
		p.join()
	p.dispatch_children(lg)
	p.join()

# As far as we're concerned, <ab> is just a <p>, so we treat them identically.
@handler("ab")
@handler("p")
def parse_p(p, para):
	# We deal with stanzas in another handler
	assert not para["rend"] == "stanza"
	p.push(tree.Tag("para"))
	if (n := get_n(para)):
		# See e.g. http://localhost:8023/display/DHARMA_INSSII0400223
		# Should be displayed like <lb/> is in the edition.
		p.push(tree.Tag("span", class_="lb"))
		p.append(f"({n})")
		p.join()
		p.append(" ")
	p.dispatch_children(para)
	p.join()

def append_meter_description(p, met):
	if prosody.is_pattern(met):
		p.append(prosody.render_pattern(met))
	elif (entry := p.get_prosody_entry(met)):
		pattern, _, _ = entry
		p.append(met)
		p.append(" (")
		p.append(pattern)
		p.append(")")
	else:
		p.append(met)

@handler("l")
def parse_l(p, l):
	p.push(tree.Tree())
	if (real := l["real"]):
		p.append("Irregular meter: ")
		append_meter_description(p, real)
		if (met := l["met"]):
			p.append("; based on ")
			append_meter_description(p, met)
	elif (met := l["met"]):
		p.append("Meter: ")
		append_meter_description(p, met)
	p.push(tree.Tag("verse-line", n=get_n(l), tip=p.pop().xml()))
	p.dispatch_children(l)
	if common.to_boolean(l["enjamb"], False):
		# #XXX should remove whitespace at end of line
		p.push(tree.Tag("span", class_="enjamb", tip="Enjambement"))
		p.append("-")
		p.join()
	p.join()

# > para-like

# < lists

"""
XXX special type for manu?

INSII2400053

réduire les espaces entre ce qui précède et suit du para + entre les items
(pas paragraphe "purs", mais sauts de lignes).

<p><list><item>...</list></p>

<p>bla bla bla <list><item>...</item></list> bla bla bla</p>

<p>bla bla bla <list><item>...</item></list></p>

<p><list><item>...</item></list> bla bla bla</p>
"""

# In HTML, we cannot have <p><ul>...</ul></p>, the <ul> or <ol> must be outside
# of <p>, so we need to generate a compatible representation. OTOH, HTML allows
# <dl> within <p>, so no special treatment is needed in this case. Still, it
# might be better to use the same structure for both.

@handler("list[@rend='description' or label]")
def parse_description_list(p, lst):
	p.push(tree.Tag("dlist"))
	# We expect a series of (label, item).
	for item in lst.find("item"):
		label = item.first("stuck-preceding-sibling::label")
		p.push(tree.Tag("key"))
		if label:
			p.dispatch_children(label)
		p.join()
		p.push(tree.Tag("value"))
		p.dispatch_children(item)
		p.join()
	p.join()

@handler("list")
def parse_list(p, lst):
	rend = lst["rend"]
	if rend not in ("plain", "bulleted", "numbered"):
		rend = "plain"
	p.push(tree.Tag("list", type=rend))
	for item in lst.find("item"):
		p.push(tree.Tag("item"))
		# XXX need a space after each item in physical, see
		# DHARMA_INSSII0501358; deal with that in the rendering
		# code
		p.dispatch_children(item)
		p.join()
	p.join()

# > lists

# I really don't like the encoding we use for <listBibl>, because there is no
# reason why a <ptr> should produce something other than a link. But we're
# stuck with that. Apparently, this was borrowed from epiDoc, see:
# https://epidoc.stoa.org/gl/latest/supp-bibliography.html
# Still doesn't make it a good idea.
@handler("listBibl")
def parse_listBibl(p, node):
	# We expect @type to be one of "primary" or "secondary", but
	# still accept other values; just put the @type in capitals, so it
	# mostly works with custom values.
	typ = node["type"]
	if typ:
		p.push(tree.Tag("head"))
		p.add_text(common.sentence_case(typ))
		p.join()
	p.dispatch_children(node)

# Title of the edited text (in the teiHeader).
@handler("titleStmt/title")
def parse_title_in_header(p, title):
	p.dispatch_children(title)

# Titles within the document body (per contrast with the title of the edition).
# EGD 10.4.2. Encoding titles.
@handler("title")
def parse_title(p, title):
	p.start_span(tip="Work title")
	if title["level"] == "a":
		p.add_text("“")
		p.dispatch_children(title)
		p.add_text("”")
	elif title["rend"] == "plain":
		p.dispatch_children(title)
	else:
		p.start_span(klass="title")
		p.dispatch_children(title)
		p.end_span()
	p.end_span()

@handler("q")
@handler("quote")
def parse_quote(p, q):
	if q["rend"] == "block":
		p.push(tree.Tag("blockquote"))
		# XXX <blockquote> cannot appear within a <p> in HTML!
		# and idem for <cit> bleow
		# https://html.spec.whatwg.org/#elements-3
		p.dispatch_children(q)
		p.join()
	else:
		p.add_text("“")
		# XXX should fix up space here
		p.dispatch_children(q)
		p.add_text("”")

@handler("cit")
def parse_cit(p, cit):
	# <cit>
	#    <quote>the text</quote>
	#    <bibl><ptr target="bib:Agrawala1983_01"/></bibl>
	# </cit>
	#
	# "the text" (Agrawala 1983)
	q = cit.first("*[name() = 'q' or name() = 'quote']")
	bibl = cit.first("bibl")
	if not bibl and not q:
		return
	if not bibl:
		return p.dispatch_children(q)
	if not q:
		return p.dispatch_children(bibl)
	if q["rend"] == "block":
		p.push(tree.Tag("blockquote"))
		p.dispatch_children(q)
		p.add_text(" (")
		p.dispatch(bibl)
		p.add_text(")")
		p.join()
	else:
		p.add_text("“")
		p.dispatch_children(q)
		p.add_text("”")
		p.add_text(" (")
		p.dispatch(bibl)
		p.add_text(")")

# We don't attempty to preserve the structure <forename>+<surname> for
# searching, because we can also have just <name>, so it's better to just have
# a simple string.
def gather_people(stmt, *paths):
	nodes = [node for path in paths for node in stmt.find(path)]
	# Sort by order of appearance in the file
	nodes.sort(key=lambda node: node.location.start)
	full_names = []
	dharma_ids = []
	for node in nodes:
		ident = node["ref"]
		if ident == "part:jodo": # John Doe, placeholder
			continue
		if ident.startswith("part:"):
			ident = ident.removeprefix("part:")
			# Use the name given in the contributors list instead of
			# the one given here.
			name = people.plain(ident)
			if name:
				common.append_unique(dharma_ids, ident)
				common.append_unique(full_names, name)
				continue
		# We should have either <forename>+<surname> or just <name>. But
		# also prepare for <surname>+<forename> or a plain string.
		first, last = node.first("forename"), node.first("surname")
		if first and last:
			name = first.text(space="preserve") + " " + last.text(space="preserve")
		else:
			name = node.text(space="preserve")
		name = common.normalize_space(name)
		common.append_unique(full_names, name)
	return full_names, dharma_ids

# We only expect this to appear at /TEI/teiHeader/fileDesc/titleStmt (and a
# single occurrence).
@handler("titleStmt")
def parse_titleStmt(p, stmt):
	# Text title.
	# We should only have a single <title> elements, but, if there are many,
	# join them into a single string.
	# The EGD prescribes to only use a plain string within <title>, but we
	# relax this rule and allow tags here. See e.g. DHARMA_INSPallava00506.
	p.push(tree.Tree())
	parts = stmt.find("title")
	for i, part in enumerate(parts):
		if i > 0:
			p.add_text(" \N{en dash} ")
		p.dispatch(part)
	p.document.title = p.pop()
	# Author of the text (only for critical editions).
	authors, _ = gather_people(stmt, "author")
	p.document.authors = authors
	# Editor(s) of the text.
	# The only allowed form is respStmt/persName, but also prepare for a few
	# other forms that are valid TEI but not valid DHARMA.
	editors, editors_ids = gather_people(stmt, "respStmt/persName", "editor", "principal", "respStmt/name")
	p.document.editors = editors
	p.document.editors_ids = editors_ids

@handler("text//roleName")
@handler("text//measure")
@handler("text//date")
@handler("text//placeName")
@handler("text//persName")
@handler("text//text")
@handler("text//term")
@handler("text//gloss")
def parse_just_dispatch_all(p, node):
	p.dispatch_children(node)

@handler("TEI") # /TEI
@handler("teiHeader") # /TEI/teiHeader
@handler("fileDesc") # /TEI/teiHeader/fileDesc
@handler("sourceDesc") # /TEI/teiHeader/fileDesc/sourceDesc
@handler("msDesc") # /TEI/teiHeader/fileDesc/sourceDesc/msDesc
@handler("msContents") # /TEI/teiHeader/fileDesc/sourceDesc/msDesc/msContents
@handler("text") # /TEI/text
@handler("body") # /TEI/text/body
def parse_just_dispatch(p, node):
	p.dispatch_children(node, only_tags=True)

@handler("publicationStmt")
@handler("editionStmt")
@handler("facsimile") # for images, will see later on
@handler("handShift")
@handler("publicationStmt") # /TEI/teiHeader/fileDesc/publicationStmt
@handler("msIdentifier") # /TEI/teiHeader/fileDesc/sourceDesc/msDesc/msIdentifier
@handler("encodingDesc") # /TEI/teiHeader/encodingDesc
@handler("revisionDesc") # /TEI/teiHeader/revisionDesc
def parse_ignore(p, node):
	pass

def parse_handDesc(p, desc):
	root = desc.first("summary") or desc
	p.push("hand_desc")
	found = False
	for para in root.find("p"):
		p.dispatch(para)
		found = True
	p.document.hand_desc = p.pop()
	if not found:
		p.document.hand_desc = None

# /TEI/teiHeader/fileDesc/sourceDesc/msDesc/msContents/summary
# We expect a single occurrence.
@handler("sourceDesc/msDesc/msContents/summary")
def parse_contents_summary(p, summ):
	# We're supposed to have either a series of <p>, or a piece of text
	# without divisions. If we have no <p>, create one and wrap the
	# whole contents into it.
	p.push(tree.Tree())
	if summ.find("p"):
		p.dispatch_children(summ)
	else:
		p.push(tree.Tag("p"))
		p.dispatch_children(summ)
		p.join()
	p.document.summary = p.pop()

# We expect a single occurrence.
@handler("sourceDesc/msDesc/physDesc/handDesc")
def parse_source_handDesc(p, desc):
	hd = desc.first("msDesc/physDesc/handDesc")
	if hd:
		parse_handDesc(p, hd)

def get_script(node):
	m = re.match(r"class:([^ ]+) maturity:(.+)", node["rendition"])
	if not m:
		return langs.get_script("")
	klass, maturity = m.groups()
	script = langs.get_script(klass)
	return script

def trim_left(strings):
	while strings:
		s = strings[0]
		if len(s) == 0 or s.isspace():
			s.delete()
			del strings[0]
			continue
		if s[0].isspace():
			s.replace_with(s.data.lstrip())
		break

def trim_right(strings):
	while strings:
		s = strings[-1]
		if len(s) == 0 or s.isspace():
			s.delete()
			strings.pop()
			continue
		if s[0].isspace():
			s.replace_with(s.data.lstrip())
		break

def squeeze(strings):
	i = 0
	while i < len(strings):
		s = strings[i]
		if len(s) == 0:
			s.delete()
			del strings[i]
			continue
		ret = re.sub(r"\s+", " ", s.data)
		if ret[0] == " " and i > 0 and strings[i - 1][-1] == " ":
			ret = ret[1:]
		if ret != s.data:
			s.replace_with(ret)
		i += 1

def cleanup_descendant_spaces(node):
	strings = node.strings()
	trim_left(strings)
	trim_right(strings)
	squeeze(strings)

def cleanup_child_spaces(node):
	strings = [child for child in node if isinstance(child, tree.String)]
	trim_left(strings)
	trim_right(strings)
	squeeze(strings)

# We're supposed to have either a series of <div> that covers all the text, or no div at all.
def gather_sections(p, div):
	p.push(div["type"])
	for child in div:
		match child:
			case tree.Tag() if child.name == "div":
				if p.within_div:
					p.end_div()
				p.dispatch(child)
			case tree.Comment() | tree.Instruction():
				pass
			case _:
				if not p.within_div:
					if isinstance(child, tree.String) and not child.strip():
						continue
					p.start_div()
				p.dispatch(child)
	if p.within_div:
		p.end_div()
	return p.pop()

def fetch_resp(resp):
	resp = people.plain(resp.removeprefix("part:")) or resp
	return html.escape(resp)

# We must process the bibliography in two steps. First, collect bibliography
# entries in div[@type='bibliography']. Then, process bibliographic references
# (Author+Date or equivalent). This order because we need to tell from the get
# go where a reference will point, which requires us to know which entries are
# present in the file-specific bibliography and which are not. (The latter
# need to be presented within the project-wide bibliography.)
def gather_biblio(p):
	for bibl in p.tree.find("//div[@type='bibliography']//listBibl/bibl[ptr]"):
		ptr = bibl.first("ptr")
		short_title = ptr["target"].removeprefix("bib:")
		if not short_title or short_title == "AuthorYear_01":
			continue
		siglum = bibl["n"]
		if siglum:
			# The same siglum might erroneously be used for several
			# entries. In this case, map it to the first one (since
			# this is what we are doing with duplicate short titles).
			p.document.sigla.setdefault(short_title, siglum)
		# The same short title might be used in several bibliographic
		# entries, possibly with different sigla, page ranges, etc.,
		# even though this is forbidden by the schema. If this happens,
		# we will just display the duplicates, but we should also take
		# care not to generate duplicate anchors in the HTML. XXX not done so far
		if short_title not in p.document.bib_entries:
			entry = biblio.Entry(short_title)
			p.document.bib_entries[short_title] = entry

# Within inscriptions, <div> shouldn't nest, except that we can have
# <div type="textpart"> within <div type="edition">.
# The DHARMA_INSEC* stuff don't follow the INS schema, too different.
# We expect:
# <div type="textpart" n="..."><head>...</head>?<note>?
@handler("div[@type='textpart']")
def parse_div_textpart(p, div):
	def make_textpart_heading():
		subtype = div["subtype"] or "part"
		p.add_text(common.sentence_case(subtype))
		if (n := get_n(div)):
			p.add_text(f" {n}")
	p.push(tree.Tag("textpart"))
	add_div_heading(p, div, make_textpart_heading)
	p.dispatch_children(div)
	p.join() # </div>

@handler("div[regex('edition|apparatus|commentary|bibliography', @type)]")
def parse_main_div(p, div):
	p.push(tree.Tree())
	add_div_heading(p, div, div["type"].title())
	p.dispatch_children(div, only_tags=True)
	setattr(p.document, div["type"], p.pop())

def add_div_heading(p, div, dflt):
	p.push("head")
	if (head := div.first("stuck-child::head")):
		# User-specified heading, use it.
		p.dispatch_children(head)
		p.visited.add(head)
		# We support notes here because the guide says so, but putting
		# them within <head>< should be preferred.
		note = head.first("stuck-following-sibling::note")
	else:
		# No user-specified heading, generate one.
		if callable(dflt):
			dflt()
		else:
			assert isinstance(dflt, str)
			p.append(dflt)
		note = div.first("stuck-child::note")
	if note:
		p.dispatch(note)
		p.visited.add(note)
	p.join()

def append_names(p, resps):
	for i, resp in enumerate(resps):
		resp = resp.removeprefix("part:")
		if i == 0:
			pass
		elif i < len(resps) - 1:
			p.add_text(", ")
		else:
			p.add_text(" and ")
		p.add_text(fetch_resp(resp))

def append_sources(p, refs):
	for i, ref in enumerate(refs):
		ref = ref.removeprefix("bib:")
		if i == 0:
			pass
		elif i < len(refs) - 1:
			p.add_text(", ")
		else:
			p.add_text(" and ")
		p.append(p.bib_reference(ref))

@handler("div[@type='translation']")
def parse_div_translation(p, div):
	def make_translation_heading():
		p.add_text("Translation")
		lang = div["lang"].split("-")[0]
		if lang and lang != "eng": # XXX normalize lang code before
			lang = langs.from_code(lang) or lang
			p.add_text(f" into {lang}")
		if (resps := div["resp"]):
			p.add_text(" by ")
			append_names(p, resps.split())
		elif (sources := div["source"]):
			p.add_text(" by ")
			append_sources(p, sources.split())
	p.push(tree.Tree())
	add_div_heading(p, div, make_translation_heading)
	p.dispatch_children(div, only_tags=True)
	p.document.translation.append(p.pop())

@handler("teiHeader/*")
def parse_in_teiHeader(p, node):
	p.dispatch_children(node, only_tags=True)

def process_file(file, mode=None):
	try:
		t = tree.parse_string(file.data, path=file.full_path)
	except tree.Error:
		doc = document.Document()
		doc.valid = False
		doc.repository = file.repo
		doc.ident = file.name
		doc.langs = [langs.Undetermined]
		doc.edition_langs = [langs.Undetermined]
		return doc
	langs.assign_languages(t)
	p = Parser(t)
	p.document.xml = tree.html_format(t)
	# When we are parsing the file, not to display it but to extract
	# metadata for the catalog, we only need to parse the teiHeader and
	# can ignore the text body. Furthermore, we need to remove footnotes
	# in the metadata; they should not be shown within the catalog.
	# (Alternatively, we could have a mouseover, but not sure it would be
	# worth it.)
	if mode == "catalog":
		for path in ("/TEI/teiHeader//title//note", "/TEI/text"):
			for node in t.find(path):
				p.visited.add(node)
	# Process the bibliography first, to gather sigla.
	# We do this early because we might need to access bibliographical
	# data when parsing e.g. the //teiHeader//msContents/summary. Note that
	# we can't even parse the div[@type='bibliography'] before other stuff
	# in the file, because this div might itself reference bibliography
	# entries. We thus need to go directly for the listBibl/bibl items.
	gather_biblio(p)
	p.dispatch(p.tree.root)
	all_langs = set()
	for node in t.find("//*"):
		all_langs.add(node.assigned_lang)
	if not all_langs:
		all_langs.add(langs.Undetermined)
	p.document.langs = sorted(all_langs)
	ed_langs = set()
	for node in t.find("//div[@type='edition']/descendant-or-self::*"):
		if node.assigned_lang.is_source:
			ed_langs.add(node.assigned_lang)
	if not ed_langs:
		ed_langs.add(langs.Undetermined)
	p.document.edition_langs = sorted(ed_langs)
	p.document.repository = file.repo
	return p.document

@common.transaction("texts")
def export_plain():
	db = common.db("texts")
	renderer = document.PlainRenderer(strip_physical=True)
	out_dir = common.path_of("plain")
	os.makedirs(out_dir, exist_ok=True)
	for (name,) in db.execute("""
		select name
		from documents natural join files where name glob 'DHARMA_INS*'
		"""):
		f = db.load_file(name)
		try:
			ret = renderer.render(process_file(f))
		except tree.Error:
			continue
		except Exception as e:
			logging.error(f"cannot process {name} ({e})")
			continue
		out_file = os.path.join(out_dir, name + ".txt")
		with open(out_file, "w") as f:
			f.write(ret)

if __name__ == "__main__":
	# export_plain()
	# exit(0)

	from dharma import texts
	@common.transaction("texts")
	def main():
		path = os.path.abspath(sys.argv[1])
		try:
			f = texts.File("/", path)
			doc = process_file(f)
			print(doc.serialize().xml())
		except BrokenPipeError:
			pass
	main()
