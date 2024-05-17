import os, sys, re, html
from urllib.parse import urlparse
from dharma import prosody, people, tree, gaiji, common, biblio, langs, document
from dharma.document import Document, Block

HANDLERS = []

def handler(path):
	def decorator(f):
		HANDLERS.append((tree.Node.match_func(path), f))
		return f
	return decorator

class Parser:

	div_level = 0

	def __init__(self, tree):
		self.tree = tree
		self.document = Document()
		self.document.tree = tree
		self.document.ident = os.path.basename(os.path.splitext(tree.file)[0])
		# Stack of blocks.
		self.blocks = [Block()]
		self.handlers = HANDLERS
		self.divs = []
		# Nodes in this set are ignored in dispatch(). These nodes
		# still remain in the tree and are still accessible from
		# within handlers.
		self.visited = set()

	@property
	def top(self):
		return self.blocks[-1]

	def push(self, name):
		b = Block(name)
		self.blocks.append(b)
		return b

	def pop(self):
		b = self.blocks.pop()
		b.finish()
		return b

	@property
	def within_div(self):
		return len(self.divs) > 1

	def clear_divs(self):
		self.divs.clear()
		self.divs.append(set())

	def add_n(self, n):
		if n != "?" and n in self.divs[-1]: # XXX no "?" mess
			return False
		self.divs[-1].add(n)
		return True

	def start_div(self, n="?"): # XXX no "?" mess
		# we could duplicate <div in log and phys, for commodity
		self.add_log("<div", n=n)
		self.divs.append(set())

	def end_div(self):
		assert self.within_div
		self.divs.pop()
		self.add_log(">div")

	def add_text(self, text):
		return self.top.add_text(text)

	def add_html(self, data, **params):
		return self.top.add_html(data, **params)

	def add_phys(self, data, **params):
		return self.top.add_phys(data, **params)

	def add_code(self, t, data=None, **params):
		return self.top.add_code(t, data, **params)

	def add_log(self, data, **params):
		return self.top.add_log(data, **params)

	def get_bib_ref(self, ref, rend="default", loc=None, siglum=False):
		entry = self.document.bib_entries.get(ref)
		if not entry:
			entry = biblio.Entry(ref)
			self.document.bib_entries[ref] = entry
		if siglum:
			siglum = self.document.sigla.get(ref)
		entry_ref = entry.reference(rend=rend, loc=loc, siglum=siglum,
			external_link=ref not in self.document.biblio)
		return entry_ref

	def add_bib_ref(self, *args, **kwargs):
		self.add_code("ref", self.get_bib_ref(*args, **kwargs))

	def get_prosody_entries(self, name):
		entries = self.document.prosody_entries.get(name)
		if entries is None:
			db = common.db("texts")
			entries = db.execute(
				"select pattern, entry_id from prosody where name = ?",
				(name,)).fetchall()
			self.document.prosody_entries[name] = entries
		return entries

	def start_item(self):
		return self.top.start_item()

	def start_span(self, **params):
		return self.top.start_span(**params)

	def end_span(self):
		return self.top.end_span()

	def dispatch(self, node):
		if node in self.visited:
			return
		match node:
			case tree.Comment() | tree.Instruction():
				return
			case tree.String():
				self.add_text(str(node).replace("'", "’"))
				return
			case tree.Tag():
				pass
			case _:
				assert 0
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

	def dispatch_children(self, node):
		for child in node:
			self.dispatch(child)

	def complain(self, msg):
		print("UNKNOWN %s" % msg)
		pass

@handler("code")
def parse_code(p, code):
	p.add_html("<code>")
	p.dispatch_children(code)
	p.add_html("</code>")

@handler("lem")
def parse_lem(p, lem):
	p.dispatch_children(lem)
	add_lemmas_links(p, lem["source"])

# When there is a <ptr target="bib:xxxxxx"/> in the apparatus, and that this
# node is not wrapped into a <bib> element, display the siglum as clickable
# element instead of Author+Data
@handler("div[@type='apparatus']//ptr")
def parse_ptr_apparatus(p, ptr):
	return parse_ptr(p, ptr, siglum=True)

@handler("ptr")
def parse_ptr(p, ptr, siglum=False):
	ref = ptr["target"].removeprefix("bib:")
	if not ref:
		return
	p.add_bib_ref(ref, siglum=siglum)

@handler("ref")
def parse_ref(p, ref):
	# See e.g. TamilNadu07
	target = ref["target"]
	if target:
		url = urlparse(target)
		# Drop the file extension if on our server (for dealing with
		# e.g. "DHARMA_INSIDENKTuhanyaru.xml").
		if not url.hostname:
			path = os.path.splitext(url.path)[0]
			url = url._replace(path=path)
			target = url.geturl()
		p.add_html(f'<a href="{target}">')
	p.dispatch_children(ref)
	if target:
		p.add_html('</a>')

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
	p.start_span(klass="lb", tip="Line start")
	p.add_text("(%s)" % loc)
	p.end_span()
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
	tip = ""
	if num["value"]:
		if num.text() != num["value"] or num["cert"] == "low":
			tip = f"Numeral {num['value']}"
	elif num["atLeast"] and num["atMost"]:
		tip = f"Numeral between {num['atLeast']} and {num['atMost']} inclusive"
	elif num["atLeast"]:
		tip = f"Numeral greater than or equal to {num['atLeast']}"
	elif num["atMost"]:
		tip = f"Numeral smaller than or equal to {num['atMost']}"
	if tip and num["cert"] == "low":
		tip += " (low certainty)"
	p.start_span(klass="num", tip=tip)
	p.dispatch_children(num)
	p.end_span()

# Try to have more precise tooltips for this. If this does not work, we fall
# back to a generic one.
@handler("supplied[@reason='subaudible']")
def parse_supplied_subaudible(p, supplied):
	if supplied.lang.is_source:
		brackets = None
		text = supplied.text()
		if text in "'’":
			tip = "<i>Avagraha</i> added by the editor to clarify the interpretation"
		elif text == ".":
			tip = "Punctuation added by the editor at semantic break"
		else:
			tip = None
	else:
		tip = "Text added to the translation for the sake of target language syntax"
		brackets = "[]"
	return parse_supplied(p, supplied, tip=tip, brackets=brackets)

# EGD "Additions to the translation"
# EGD "Marking up restored text"
# EGD "The basis of restoration"
supplied_tbl = {
	# EGD: "words added to the translation for the sake of target language
	# syntax"
	"subaudible": ("⟨⟩", "Editorial addition to clarify interpretation"),
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
@handler("supplied")
def parse_supplied(p, supplied, tip=None, brackets=None):
	base_brackets, base_tip = supplied_tbl.get(supplied["reason"], supplied_tbl["lost"])
	if not tip:
		tip = base_tip
	if not brackets:
		brackets = base_brackets
	assert brackets
	if supplied["cert"] == "low":
		tip += " (low certainty)"
	evidence = supplied["evidence"]
	if evidence == "parallel":
		tip += "; restoration based on parallel"
	elif evidence == "previouseditor":
		tip += "; restoration based on previous edition (not assessable)"
	p.start_span(klass="supplied", tip=tip)
	p.add_html(brackets[0])
	p.dispatch_children(supplied)
	if supplied["reason"] in ("subaudible", "explanation") \
		and supplied["cert"] == "low":
		p.add_html("?")
	p.add_html(brackets[1])
	p.end_span()

# § Premodern insertion
# OK
add_place_tbl = {
	"inline": "within the same line or in the immediate vicinity of the locus",
	"below": "below the line",
	"above": "above the line",
	"top": "in the top margin",
	"bottom": "in the bottom margin",
	"left": "in the left margin",
	"right": "in the right margin",
	"overstrike": "made in the space where a previous string of text has been erased",
	"unspecified": ": no location information available",
}
@handler("add")
def parse_add(p, node, dele=None):
	place = node["place"]
	tip = add_place_tbl.get(place, add_place_tbl["unspecified"])
	tip = f"Scribal addition {tip}"
	if dele:
		tip += f' (overwritten text: <span class="del">⟦{html.escape(dele)}⟧</span>)'
	p.start_span(klass="add", tip=tip)
	p.add_html("⟨⟨")
	p.dispatch_children(node)
	p.add_html("⟩⟩")
	p.end_span()

# § Premodern deletion
# OK
del_rend_tbl = {
	"strikeout": "text struck through or cross-hatched",
	"ui": "combined application of vowel markers <i>u</i> and <i>i</i> to characters to be deleted",
	"other": "",
	"corrected": "corrected text",
}
@handler("del")
def parse_del(p, node, add=None):
	tip = del_rend_tbl.get(node["rend"], "")
	if tip:
		tip = f"Scribal deletion: {tip}"
	else:
		tip = "Scribal deletion"
	if add:
		tip += f' (replacement text: <span class="add">⟨⟨{html.escape(add)}⟩⟩</add>)'
	p.start_span(klass="del", tip=tip)
	p.add_html("⟦")
	p.dispatch_children(node)
	p.add_html("⟧")
	p.end_span()

# § Premodern correction
# OK
@handler("subst")
def parse_subst(p, subst):
	# (del, add)
	# Use the text of <add> for search
	#XXX schema is valid?
	children = subst.children()
	if len(children) == 2 and children[0].matches("del") and children[1].matches("add"):
		# TODO should be rendered into a block, not necessarily plain text!
		parse_del(p, children[0], children[1].text())
		parse_add(p, children[1], children[0].text())
	else:
		p.dispatch_children(subst)
	# add: (overwritten text: X)
	# del: (replacement text: X)

# We also deal with notes in <app>
# TODO there are attributes,see EGD
@handler("note")
def parse_note(p, note):
	# Avoid nesting notes
	if p.top.name == "note":
		p.dispatch_children(note)
		return
	p.add_log("=note", n=len(p.document.notes) + 1)
	p.push("note")
	p.dispatch_children(note)
	ret = p.pop()
	p.document.notes.append(ret)

@handler("foreign")
def parse_foreign(p, foreign):
	p.add_html("<i>")
	p.dispatch_children(foreign)
	p.add_html("</i>")

# <milestones

def get_n(node, default="?"):
	n = node["n"]
	if not n:
		return default
	n = n.replace("_", " ").replace("-", "\N{en dash}")
	return n

def milestone_n(p, node):
	n = get_n(node)
	if not p.add_n(n):
		node.add_error("@n is not unique")
	return n

def milestone_break(node):
	brk = node["break"]
	if brk not in ("yes", "no"):
		brk = "yes"
	return brk == "yes"

def milestone_unit_type(milestone):
	unit = milestone["unit"] or "column"
	typ = milestone["type"]
	if typ not in ("pagelike", "gridlike"):
		typ = "gridlike"
	return unit, typ

@handler("milestone")
# TODO milestone type="ref"
def parse_milestone(p, milestone):
	n = milestone_n(p, milestone)
	brk = milestone_break(milestone)
	unit, typ = milestone_unit_type(milestone)
	next_sibling = milestone.stuck_following_sibling()
	if next_sibling and next_sibling.name == "label":
		label = next_sibling.text() # XXX handle markup
	else:
		label = None
	p.add_phys("=" + unit, type=typ, n=n, brk=brk, label=label)

@handler("lb")
def parse_lb(p, elem):
	n = milestone_n(p, elem)
	brk = milestone_break(elem)
	# On alignment, EGD §7.5.2
	m = re.match(r"^text-align:\s?(right|center|left|justify)$", elem["style"])
	if m:
		align = m.group(1)
	else:
		# If not given, we assume it is not important and omit the
		# alignment from the tooltip.
		align = None
	p.add_phys("line", n=n, brk=brk, align=align)

@handler("fw")
def parse_fw(p, fw):
	# We deal with this within parse_pb.
	pass

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
def parse_pb(p, elem):
	n = milestone_n(p, elem)
	brk = milestone_break(elem)
	p.add_phys("{page", n=n, brk=brk)
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
			p.start_span(klass="fw", tip="Foliation work")
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

# >milestones

# <editorial

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

# OK
@handler("sic")
def parse_sic(p, sic, corr=None):
	klass = "sic"
	tip = "Incorrect text"
	if corr:
		tip += ' (emendation: <span class="corr">⟨%s⟩</span>)' % html.escape(corr)
	else:
		klass = [klass, "standalone"]
	p.start_span(klass=klass, tip=tip)
	p.add_html("¿")
	mark = len(p.top.code)
	p.dispatch_children(sic)
	text_to_html(p, mark)
	p.add_html("?")
	p.end_span()

# OK
@handler("corr")
def parse_corr(p, corr, sic=None):
	klass = "corr"
	tip = "Emended text"
	if sic:
		tip += ' (original: <span class="sic">¿%s?</span>)' % html.escape(sic)
	else:
		klass = [klass, "standalone"]
	p.start_span(klass=klass, tip=tip)
	p.add_html('⟨')
	p.dispatch_children(corr)
	p.add_html('⟩')
	p.end_span()

# OK
@handler("orig")
def parse_orig(p, orig, reg=None):
	klass = "orig"
	tip = "Non-standard text"
	if reg:
		tip += ' (standardisation: <span class="reg">⟨%s⟩</span>)' % html.escape(reg)
	else:
		klass = [klass, "standalone"]
	p.start_span(klass=klass, tip=tip)
	p.add_html("¡")
	mark = len(p.top.code)
	p.dispatch_children(orig)
	text_to_html(p, mark)
	p.add_html("!")
	p.end_span()

# OK
@handler("reg")
def parse_reg(p, reg, orig=None):
	klass = "reg"
	tip = "Standardised text"
	if orig:
		tip += ' (original: <span class="orig">¡%s!</span>)' % html.escape(orig)
	else:
		klass = [klass, "standalone"]
	p.start_span(klass=klass, tip=tip)
	p.add_html("⟨")
	p.dispatch_children(reg)
	p.add_html("⟩")
	p.end_span()

# TODO For now there is no nesting of <choice>, but it is allowed in some
# cases. This happens within <orig> and <reg> so must deal with it when parsing
# these tags.
@handler("choice")
def parse_choice(p, node):
	children = node.children()
	if all(child.name == "unclear" for child in children):
		# <choice>(<unclear>...</unclear>)+</choice>
		# In this case for search and plain just keep the text of the 1st unclear.
		p.start_span(klass="choice-unclear", tip="Unclear (several possible readings)")
		p.add_html("(")
		mark = -1
		for child in children:
			if mark >= 0:
				p.add_html("/")
			p.dispatch_children(child)
			if mark < 0:
				mark = len(p.top.code)
		text_to_html(p, mark)
		p.add_html(")")
		p.end_span()
	else:
		# <choice><sic>...</sic><corr>...</corr></choice>
		# OR
		# <choice><orig>...</orig><reg>...</reg></choice>
		#
		# For searching keep <corr> and <reg>, ignore the rest.
		# TODO should be rendered into a block, not necessarily plain text!
		if len(children) == 2 and children[0].name == "sic" and children[1].name == "corr":
			parse_sic(p, children[0], children[1].text())
			parse_corr(p, children[1], children[0].text())
		elif len(children) == 2 and children[0].name == "orig" and children[1].name == "reg":
			parse_orig(p, children[0], children[1].text())
			parse_reg(p, children[1], children[0].text())
		else:
			p.dispatch_children(node)

# >editorial

# Valid cases are:
#
#	<space [type="semantic"]/> (shorthand is '_')
#	<space [type="semantic"] quantity=... unit="character"/>
#	<space type="vacat" quantity=... unit="character"/>
#	<space type="(binding-hole|descender|ascender|defect|feature)"/>
#	<space type="unclassified"/>
#	<space type="unclassified" quantity=... unit="character"/>
#
# OK
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
	typ = space["type"]
	if typ not in space_types:
		typ = "semantic"
	if typ in ("semantic", "vacat", "unclassified"):
		quant = space["quantity"]
		if not quant.isdigit():
			quant = "1"
		quant = int(quant)
		if quant < 1:
			quant = 1
		unit = space["unit"]
		if unit != "character":
			unit = "character"
	info = space_types[typ]
	tip = info["tip"]
	text = info["text"]
	if typ in ("semantic", "vacat", "unclassified"):
		if quant < 2:
			tip = f"small {typ} space (from barely noticeable to less than two average character widths in extent)"
		else:
			tip = f"large {typ} space (about {quant} {unit}s wide)"
		text *= quant
	p.start_span(klass="space", tip=common.sentence_case(tip))
	p.add_html(text, physical=True, logical=False, full=True)
	p.end_span()

# <abbreviations

@handler("abbr")
def parse_abbr(p, node):
	p.start_span(klass="abbr", tip="Abbreviated text")
	p.dispatch_children(node)
	p.end_span()

@handler("ex")
def parse_ex(p, node):
	p.start_span(klass="abbr-expansion", tip="Abbreviation expansion")
	p.add_html("(")
	p.dispatch_children(node)
	p.add_html(")")
	p.end_span()

@handler("am")
def parse_am(p, am):
	p.start_span(klass="abbr-mark", tip="Abbreviation mark")
	p.dispatch_children(am)
	p.end_span()

@handler("expan")
def parse_expan(p, node):
	p.dispatch_children(node)

# >abbreviations

# TODO more styling
@handler("seg")
def parse_seg(p, seg):
	first = seg.first("*")
	if first and first.name == "gap":
		# We deal with this within parse_gap
		p.dispatch_children(seg)
		return
	rend = seg["rend"].split()
	if "pun" in rend:
		p.start_span(klass="pun", tip="Pun (<i>ślesa</i>)")
		p.add_html("{")
	if "check" in rend:
		p.start_span(klass="check", tip="To check")
	if seg["cert"] == "low":
		p.start_span(klass="check-uncertain", tip="Uncertain segment")
		p.add_html("¿")
	p.dispatch_children(seg)
	if seg["cert"] == "low":
		p.add_html("?")
		p.end_span()
	if "check" in rend:
		p.end_span()
	if "pun" in rend:
		p.add_html("}")
		p.end_span()

@handler("div[@type='translation']//gap[@reason='ellipsis']")
def handle_gap_ellipsis(p, gap):
	p.start_span(tip="Untranslated segment")
	p.add_html("\N{horizontal ellipsis}", plain=True)
	p.end_span()

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
	# TODO merge consecutive values as in [ca.10x – – – ⏑ – – abc] in editorial

def parse_g_numeral(p, node):
	assert node["type"] == "numeral"
	m = re.match(r"([0-9]+)/([0-9]+)", node.text())
	if not m:
		# No special formatting
		p.dispatch_children(node)
		return
	num, den = m.groups()
	p.add_html(f"<sup>{num}</sup>\N{fraction slash}<sub>{den}</sub>")

@handler("g")
def parse_g(p, node):
	# <g type="...">\.</g> for punctuation marks
	# <g type="...">§+</g> for space fillers
	# <g type="..."></g> in the other cases viz. for symbols whose functions is unclear
	# The guide talks about subtype, but we don't allow it for now.
	t = node["type"] or "symbol"
	# Quirk with @subtype, shouldn't have to do this
	if t == "symbol" and node["subtype"]:
		t = node["subtype"]
	if t == "numeral":
		return parse_g_numeral(p, node)
	text = node.text()
	if text == ".":
		cat = "punctuation"
	elif text.startswith("§"):
		cat = "space-filler"
	else:
		cat = "uninterpreted"
	p.document.gaiji.add(t)
	info = gaiji.get(t)
	tip = f"symbol: {info['description']}"
	if cat != "uninterpreted":
		tip = f"{cat} {tip}"
	tip = common.sentence_case(tip)
	if info["text"]:
		p.start_span(klass="symbol", tip=tip)
		p.add_html(html.escape(info["text"]), plain=True)
		p.end_span()
	else:
		p.start_span(klass="symbol-placeholder", tip=tip)
		p.add_html(html.escape("<%s>" % info["name"]), plain=True)
		p.end_span()
	# had '<img alt="%s" class="svg" src="%s"/>' % (info["name"], info["img"]))

# OK
@handler("unclear")
def parse_unclear(p, node):
	tip = "Unclear text"
	if node["cert"] == "low":
		tip = "Very unclear text"
	reason = node["reason"]
	if reason:
		if reason == "eccentric_ductus":
			reason = f"<i>{reason}</i>"
		tip += f" ({reason.replace('_', ' ')})"
	p.start_span(klass="unclear", tip=tip)
	p.add_html("(")
	p.dispatch_children(node)
	if node["cert"] == "low":
		p.add_html("?")
	p.add_html(")")
	p.end_span()

# EGD "Editorial deletion (suppression)"
@handler("surplus")
def parse_surplus(p, node):
	p.start_span(klass="surplus", tip="Superfluous text erroneously added by the scribe")
	p.add_html("{")
	p.dispatch_children(node)
	p.add_html("}")
	p.end_span()

def print_as_grantha(p, node): # XXX cannot nest <div> within <p>
	#p.add_html('<div class="grantha">')
	p.dispatch_children(node)
	#p.add_html('</div>')

@handler("ab")
def parse_ab(p, ab):
	p.add_log("<para")
	if get_script(ab).ident == "grantha":
		print_as_grantha(p, ab)
	else:
		p.dispatch_children(ab)
	p.add_log(">para")

# XXX we have intervening <lb/>, etc. within <hi>, so when rendering the
# physical display, must use <div> for some of these.
hi_table = {
	"italic": "i",
	"bold": "b",
	"superscript": "sup",
	"subscript": "sub",
	"check": {"klass": "check"},
	"grantha": {"klass": "grantha", "tip": "Grantha text"},
}
@handler("hi")
def parse_hi(p, hi):
	rends = hi["rend"].split()
	tags = list(filter(None, (hi_table.get(rend) for rend in rends)))
	for tag in tags:
		if isinstance(tag, str):
			p.add_html("<%s>" % tag)
		else:
			p.start_span(**tag)
	p.dispatch_children(hi)
	tags.reverse()
	for tag in tags:
		if isinstance(tag, str):
			p.add_html("</%s>" % tag)
		else:
			p.end_span()

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

@handler("lg")
@handler("p[@rend='stanza']")
def parse_lg(p, lg):
	n = get_n(lg, default="")
	if n.isdigit():
		n = to_roman(int(n))
	met = lg["met"]
	if not met:
		pass
	elif prosody.is_pattern(met):
		met = prosody.render_pattern(met)
	else:
		name = html.escape(common.sentence_case(met))
		entries = p.get_prosody_entries(met)
		if len(entries) == 1:
			pattern, entry_id = entries[0]
			if pattern:
				met = f'<span data-tip="{html.escape(pattern)}">{name}</span>'
			met = f'<a href="/prosody#prosody-{entry_id}">{met}</a>'
		elif len(entries) > 1:
			patterns = " or ".join(html.escape(pattern) for pattern, _ in entries if pattern)
			if patterns:
				met = f'<span data-tip="{patterns}">{met}</span>'
	if n or met:
		p.add_log("<head", level=6)
		if n and met:
			p.add_html(f"{n}. {met}", plain=True)
		elif n:
			p.add_html(f"{n}", plain=True)
		elif met:
			p.add_html(f"{met}", plain=True)
		p.add_log(">head", level=6)
	numbered = len(lg.find("l")) > 4
	p.add_log("<verse", numbered=numbered)
	if get_script(lg).ident == "grantha":
		print_as_grantha(p, lg)
	else:
		p.dispatch_children(lg)
	p.add_log(">verse")

@handler("p")
def parse_p(p, para):
	# We deal with this elsewhere
	assert not para["rend"] == "stanza"
	p.add_log("<para")
	if para["n"]:
		# See e.g. http://localhost:8023/display/DHARMA_INSSII0400223
		# Should be displayed like <lb/> in the edition.
		n = html.escape(get_n(para))
		p.add_html(f'<span class="lb" data-tip="Line start">({n})</span>')
		p.add_html(" ")
	if get_script(para).ident == "grantha":
		print_as_grantha(p, para)
	else:
		p.dispatch_children(para)
	p.add_log(">para")

@handler("l")
def parse_l(p, l):
	n = get_n(l)
	tip = ""
	met = l["met"]
	if met:
		if prosody.is_pattern(met):
			met = prosody.render_pattern(met)
		else:
			name = html.escape(met)
			entries = p.get_prosody_entries(met)
			if entries:
				met = f'{name} ({" or ".join(p for p, _ in entries if p)})'
			else:
				met = name
		tip = f'Meter: {met}'
	real = l["real"]
	if real:
		if prosody.is_pattern(real):
			real = prosody.render_pattern(real)
		else:
			real = html.escape(real)
		tip = f'Irregular meter: {real}'
		if met:
			tip += f'; based on {met}'
	p.add_log("<line", n=n, tip=tip)
	p.dispatch_children(l)
	enjamb = common.to_boolean(l["enjamb"], False)
	if enjamb:
		p.start_span(klass="enjamb", tip="Enjambement")
		p.add_html("-")
		p.end_span()
	p.add_log(">line", n=n, enjamb=enjamb)

	if prosody.is_pattern(met):
		met = prosody.render_pattern(met)
	else:
		name = html.escape(common.sentence_case(met))
		entries = p.get_prosody_entries(met)

def is_description_list(nodes):
	if len(nodes) % 2: # XXX watch out for fucked text
		return False
	for i in range(0, len(nodes), 2):
		label = nodes[i]
		item = nodes[i + 1]
		if label.name != "label" or item.name != "item":
			return False
	return True

@handler("list")
def parse_list(p, list):
	typ = list["rend"]
	if typ not in ("plain", "bulleted", "numbered", "description"):
		typ = "plain"
	children = list.children()
	if is_description_list(children): # try to infer it
		typ = "description"
	p.add_log("<list", type=typ)
	if typ == "description":
		# (label, item)*
		for i in range(0, len(children), 2):
			label = children[i]
			item = children[i + 1]
			if label.name != "label" or item.name != "item":
				continue
			p.add_log("<key")
			p.dispatch_children(label)
			p.add_log(">key")
			p.add_log("<value")
			p.dispatch_children(item)
			p.add_log(">value")
	else:
		for item in list.find("item"):
			p.add_log("<item")
			# need a space after each item in physical, see
			# DHARMA_INSSII0501358
			p.add_html(" ", logical=False, plain=False)
			p.dispatch_children(item)
			p.add_log(">item")
	p.add_log(">list", type=typ)

extract_bib_ref = prosody.extract_bib_ref

def extract_bibl_items(p, listBibl):
	ret = []
	for rec in listBibl.find("bibl[ptr[@target and @target!='bib:AuthorYear_01']]"):
		ref, loc = extract_bib_ref(rec)
		if not ref:
			continue
		ret.append((rec, ref, loc))
	return ret

@handler("label")
def parse_label(p, label):
	pass # We deal with this in other handlers

@handler("listBibl")
def parse_listBibl(p, node):
	recs = extract_bibl_items(p, node)
	# Avoid displaying "Primary" or "Secondary" if there is nothing there.
	if not recs:
		return
	typ = node["type"]
	if typ:
		p.add_log("<head")
		p.add_text(common.sentence_case(typ))
		p.add_log(">head")
	for rec, ref, loc in recs:
		data = biblio.Entry(ref).contents(loc=loc, n=rec["n"])
		p.add_code("bib", data)

@handler("bibl")
def parse_bibl(p, node):
	rend = node["rend"]
	if rend not in ("omitname", "ibid", "default"):
		rend = "default"
	ref, loc = extract_bib_ref(node)
	if not ref:
		return
	p.add_bib_ref(ref, rend=rend, loc=loc)

@handler("titleStmt/title")
def parse_title_in_header(p, title):
	p.dispatch_children(title)

@handler("title")
# EGD 10.4.2. Encoding titles.
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
def parse_q(p, q):
	if q["rend"] == "block":
		p.add_log("<blockquote")
		p.dispatch_children(q)
		p.add_log(">blockquote")
	else:
		p.add_html("“")
		p.dispatch_children(q)
		p.add_html("”")

@handler("quote")
def parse_quote(p, quote):
	return parse_q(p, quote)

@handler("cit")
def parse_cit(p, cit):
	# <cit>
	#    <quote>the text</quote>
	#    <bibl><ptr target="bib:Agrawala1983_01"/></bibl>
	# </cit>
	#
	# "the text" (Agrawala 1983)
	children = cit.children()
	if len(children) != 2 or children[0].name not in ("q", "quote") \
		or children[1].name != "bibl":
		p.dispatch_children(p)
		return
	q, bibl = children
	if q["rend"] == "block":
		p.add_log("<blockquote")
		p.dispatch_children(q)
		p.add_text(" (")
		p.dispatch(bibl)
		p.add_text(")")
		p.add_log(">blockquote")
	else:
		p.add_html("“")
		p.dispatch_children(q)
		p.add_html("”")
		p.add_text(" (")
		p.dispatch(bibl)
		p.add_text(")")

def gather_people(stmt, *paths):
	nodes = [node for path in paths for node in stmt.find(path)]
	nodes.sort(key=lambda node: node.location.start)
	full_names = []
	dharma_ids = []
	for node in nodes:
		ident = node["ref"]
		if ident and ident.startswith("part:"):
			if ident == "part:jodo": # John Doe, placeholder
				continue
			ident = ident.removeprefix("part:")
			name = people.plain(ident)
			if not name:
				continue # XXX keep the id in this case?
			common.append_unique(dharma_ids, ident)
		else:
			name = common.normalize_space(node.text(space="preserve"))
			if not name:
				continue
		common.append_unique(full_names, name)
	return full_names, dharma_ids

@handler("titleStmt")
def parse_titleStmt(p, stmt):
	# We only have several <title> in DiplEd and CritEd and INSEC, not in
	# normal INS files.
	p.push("title")
	titles = stmt.find("title")
	for i, title in enumerate(titles):
		if i > 0:
			p.add_text(" \N{en dash} ")
		p.dispatch_children(title)
	p.document.title = p.pop()
	p.push("author")
	authors, _ = gather_people(stmt, "author")
	for author in authors:
		p.start_item()
		p.add_text(author)
	p.document.author = p.pop()
	p.push("editors")
	editors, editors_ids = gather_people(stmt, "editor", "principal", "respStmt/persName")
	for editor in editors:
		p.start_item()
		p.add_text(editor)
	p.document.editors = p.pop()
	p.document.editors_ids = editors_ids

@handler("roleName")
@handler("measure")
@handler("date")
@handler("placeName")
@handler("persName")
@handler("fileDesc")
@handler("teiHeader")
@handler("text")
@handler("TEI")
@handler("term")
@handler("gloss")
def parse_just_dispatch(p, node):
	p.dispatch_children(node)

@handler("publicationStmt")
@handler("editionStmt")
@handler("facsimile") # for images, will see later on
def parse_ignore(p, node):
	pass

@handler("sourceDesc")
def parse_sourceDesc(p, desc):
	summ = desc.first("msDesc/msContents/summary")
	if not summ:
		return
	# remove paragraphs
	for para in summ.find(".//p"):
		para.unwrap()
	p.push("summary")
	p.dispatch_children(summ)
	p.document.summary = p.pop()

def get_script(node):
	m = re.match(r"class:([^ ]+) maturity:(.+)", node["rendition"])
	if not m:
		return langs.get_script("")
	klass, maturity = m.groups()
	script = langs.get_script(klass)
	return script

# Within inscriptions, <div> shouldn't nest, except that we can have
# <div type="textpart"> within <div type="edition">.
# All the DHARMA_INSEC* stuff don't follow the ins schema, too different.
@handler("div[@type='textpart']")
def parse_div(p, div):
	n = milestone_n(p, div)
	# rend style subtype
	# <head> is supposed to only occur in this context in inscriptions, but
	# in fact we don't really care, might allow it somewhere else
	p.start_div(n=n)
	if (child := div.stuck_child()) and child.matches("head"):
		p.add_log("<head")
		p.add_text(n)
		p.add_text(". ")
		p.dispatch_children(child)
		p.add_log(">head")
		p.visited.add(child)
	p.dispatch_children(div)
	p.end_div()

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

def process_translation(p, div):
	p.push("title")
	p.add_text("Translation")
	lang = div["lang"].split("-")[0]
	if lang:
		lang = html.escape(langs.from_code(lang) or lang)
		p.add_text(f" into {lang}")
	if (resp := div["resp"]):
		p.add_text(" by ")
		resps = resp.split()
		for i, resp in enumerate(resps):
			if i == 0:
				pass
			elif i < len(resps) - 1:
				p.add_text(", ")
			else:
				p.add_text(" and ")
			p.add_html(fetch_resp(resp))
	if (source := div["source"]):
		ref = source.removeprefix("bib:")
		p.add_text(" by ")
		p.add_html(str(p.get_bib_ref(ref)))
	# If we have a note as first child, we expect the note to bear
	# @type='credit', but even if not so we consider the note as
	# belonging to the title.
	# TODO thus do the same for every section: if the section starts with
	# a note not preceded by non-blank text, treat the note as part of
	# the section's title.
	if (child := div.stuck_child()) and child.matches("note"):
		p.dispatch(child)
		p.visited.add(child)
	title = p.pop().render_logical()
	trans = gather_sections(p, div)
	if not trans:
		return
	trans.title = title
	return trans

def gather_biblio(p, body):
	for bibl in body.find("//listBibl/bibl"):
		siglum = get_n(bibl)
		ptr = bibl.first("ptr")
		if not ptr:
			continue
		target = ptr["target"]
		if not target.startswith("bib:"):
			continue
		target = target.removeprefix("bib:")
		# TODO add checks
		if siglum:
			p.document.sigla[target] = siglum
		p.document.biblio.add(target)

@handler("""div[@type='edition' or @type='apparatus' or @type='commentary'
	or @type='bibliography']""")
def parse_div_edition(p, div):
	p.clear_divs()
	setattr(p.document, div["type"], gather_sections(p, div))

@handler("div[@type='translation']")
def parse_div_translation(p, div):
	p.clear_divs()
	if (trans := process_translation(p, div)):
		p.document.translation.append(trans)

@handler("body")
def parse_body(p, body):
	gather_biblio(p, body)
	p.dispatch_children(body)

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
	to_delete = [
		"//teiHeader/encodingDesc",
		"//teiHeader/revisionDesc",
		"//publicationStmt",
	]
	if mode == "catalog":
		to_delete += [
			"//teiHeader//title//note",
		]
		p.visited.add(t.first("//body"))
	for path in to_delete:
		for node in t.find(path):
			node.delete()
	p.dispatch(p.tree.root)
	all_langs = set()
	for node in t.find("//*"):
		all_langs.add(node.lang)
	if not all_langs:
		all_langs.add(langs.Undetermined)
	p.document.langs = sorted(all_langs)
	ed_langs = set()
	for node in t.find("//div[@type='edition']/descendant-or-self::*"):
		if node.lang.is_source:
			ed_langs.add(node.lang)
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
		out_file = os.path.join(out_dir, name + ".txt")
		with open(out_file, "w") as f:
			f.write(ret)

if __name__ == "__main__":
	export_plain()
	exit(0)
	path = sys.argv[1]
	data = open(path, "rb").read()
	try:
		doc = process_file(path, data) # XXX needs change
		print(doc.apparatus)
	except BrokenPipeError:
		pass
