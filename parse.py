import os, sys, re, io, copy, html, unicodedata
from urllib.parse import urlparse
from dharma import prosody, people, tree, gaiji, config, unicode, biblio
from dharma.document import Document, Block

class Parser:

	div_level = 0

	def __init__(self, tree, handlers):
		self.tree = tree
		self.document = Document()
		self.document.ident = os.path.basename(os.path.splitext(tree.path)[0])
		# Stack of blocks.
		self.blocks = [Block()]
		self.handlers = handlers
		self.divs = []

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

	def start_item(self):
		return self.top.start_item()

	def start_span(self, **params):
		return self.top.start_span(**params)

	def end_span(self):
		return self.top.end_span()

	def dispatch(self, node):
		if node.type in ("comment", "instruction"):
			return
		if node.type == "string":
			self.add_text(str(node).replace("'", "’"))
			return
		assert node.type == "tag"
		f = self.handlers.get(node.name)
		if not f:
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

	def dispatch_tags(self, node):
		for child in node:
			if not node.type == "tag":
				continue
			self.dispatch(child)

	def complain(self, msg):
		print("UNKNOWN %s" % msg)
		pass

def parse_lem(p, lem):
	p.dispatch_children(lem)

def parse_ptr(p, ptr):
	ref = ptr["target"]
	if not ref.startswith("bib:"):
		return
	ref = ref.removeprefix("bib:")
	p.add_code("ref", ref, rend="default", loc=[], missing=ref not in p.document.biblio)

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
		p.add_html(f'</a>')

def parse_rdg(p, rdg):
	p.start_span(klass="reading", tip="Reading")
	p.dispatch_children(rdg)
	p.end_span()
	sources = [source.removeprefix("bib:") for source in rdg["source"].split()]
	if not sources:
		return
	for ref in sources:
		p.add_text(" ")
		siglum = p.document.sigla.get(ref)
		p.add_code("ref", ref, rend="default", loc=[], siglum=siglum, missing=ref not in p.document.biblio)

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

def parse_listApp(p, listApp):
	apps = listApp.find("app")
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

def parse_num(p, num):
	# for now we don't deal with @value, @atLeast and @atMost
	p.dispatch_children(num)

# EGD "Additions to the translation"
# EGD "Marking up restored text"
# EGD "The basis of restoration"
supplied_tbl = {
	# EGD: "words added to the translation for the sake of target language
	# syntax"
	"subaudible": ("[]", "Text added to the translation for the sake of target language syntax"),
	# EGD: "words implied by the context and added to the translation for
	# the sake of clarification or disambiguation"
	"explanation": ("()", "Text implied by the context and added to the translation for the sake of clarification or disambiguation"),
	# EGD: "lost" and "omitted" indicate "segments of translation corresponding
	# to text restored by the editor in the original" (they are used both
	# in the edition and in the translation)
	"lost": ("[]", "Lost text"),
	"omitted": ("⟨⟩", "Omitted text"),
	# EGD under "Marking up restored text" says that "undefined" is used when it's not possible
	# to tell whether we have "lost" or "omitted"
	"undefined": ("[]", "Lost or omitted text") # manu: trouver autre texte pour infobulle
}
# OK
def parse_supplied(p, supplied):
	seps, tip = supplied_tbl.get(supplied["reason"], supplied_tbl["lost"])
	if supplied["cert"] == "low":
		tip += " (low certainty)"
	evidence = supplied["evidence"]
	if evidence == "parallel":
		tip += "; restoration based on previous edition (not assessable)"
	elif tip == "previouseditor":
		tip += "; restoration based on parallel"
	p.start_span(klass="supplied", tip=tip)
	if seps:
		p.add_html(seps[0])
	p.dispatch_children(supplied)
	if seps:
		p.add_html(seps[1])
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
	"overstrike": " made in the space where a previous string of text has been erased",
	"unspecified": "(no location information available)",
}
def parse_add(p, node):
	place = node["place"]
	tip = add_place_tbl.get(place, add_place_tbl["unspecified"])
	p.start_span(klass="add", tip=f"Scribal addition {tip}")
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
def parse_del(p, node):
	tip = del_rend_tbl.get(node["rend"], "")
	if tip:
		tip = f"Scribal deletion ({tip})"
	else:
		tip = "Scribal deletion"
	p.start_span(klass="del", tip=tip)
	p.add_html("⟦")
	p.dispatch_children(node)
	p.add_html("⟧")
	p.end_span()

# § Premodern correction
# OK
def parse_subst(p, subst):
	# (del, add)
	# Use the text of <add> for search
	p.dispatch_children(subst)

# We also deal with notes in <app>
# TODO there are attributes,see EGD
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

def parse_foreign(p, foreign):
	p.add_html("<i>")
	p.dispatch_children(foreign)
	p.add_html("</i>")

# <milestones

def milestone_n(p, node):
	n = node["n"]
	if not n:
		n = "?"
	n = n.replace("_", " ")
	if not p.add_n(n):
		node.bad("@n is not unique")
	return n

def milestone_break(node):
	brk = node["break"]
	if brk not in ("yes", "no"):
		brk = "yes"
	return brk == "yes"

milestone_units = "block column face faces fragment item segment zone".split()

def milestone_unit_type(milestone):
	unit = milestone["unit"] or "column"
	typ = milestone["type"]
	if typ not in ("pagelike", "gridlike"):
		typ = "gridlike"
	return unit, typ

def parse_milestone(p, milestone):
	n = milestone_n(p, milestone)
	brk = milestone_break(milestone)
	unit, typ = milestone_unit_type(milestone)
	next_sibling = milestone.next
	if next_sibling and next_sibling.name == "label":
		label = next_sibling.text() # XXX markup?
	else:
		label = None
	p.add_phys("=" + unit, type=typ, n=n, brk=brk, label=label)

def parse_lb(p, elem):
	n = milestone_n(p, elem)
	brk = milestone_break(elem)
	# On alignment, EGD §7.5.2
	m = re.match(r"^text-align:\s*(right|center|left|justify)\s*$", elem["style"])
	if m:
		align = m.group(1)
	else:
		align = "left"
	p.add_phys("line", n=n, brk=brk)

def parse_fw(p, fw):
	# We deal with this within parse_pb.
	pass

def parse_pb(p, elem):
	n = milestone_n(p, elem)
	brk = milestone_break(elem)
	p.add_phys("{page", n=n, brk=brk)
	while True:
		fw = elem.next
		if not fw or not fw.name == "fw":
			break
		p.start_span(klass="fw", tip="Foliation work")
		if fw["place"]:
			p.add_text(f"{fw['place']}: ")
		p.dispatch_children(fw)
		p.add_text(" ")
		p.end_span()
		elem = fw
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
def parse_sic(p, sic, corr=None):
	tip = "Incorrect text"
	if corr:
		tip += ' (emendation: <span class="corr">⟨%s⟩</span>)' % html.escape(corr)
	p.start_span(klass="sic", tip=tip)
	p.add_html("¿")
	mark = len(p.top.code)
	p.dispatch_children(sic)
	text_to_html(p, mark)
	p.add_html("?")
	p.end_span()

# OK
def parse_corr(p, corr, sic=None):
	tip = "Emended text"
	if sic:
		tip += ' (original: <span class="sic">¿%s?</span>)' % html.escape(sic)
	p.start_span(klass="corr", tip=tip)
	p.add_html('⟨')
	p.dispatch_children(corr)
	p.add_html('⟩')
	p.end_span()

# OK
def parse_orig(p, orig, reg=None):
	tip = "Non-standard text"
	if reg:
		tip += ' (standardisation: <span class="reg">⟨%s⟩</span>)' % html.escape(reg)
	p.start_span(klass="orig", tip=tip)
	p.add_html("¡")
	mark = len(p.top.code)
	p.dispatch_children(orig)
	text_to_html(p, mark)
	p.add_html("!")
	p.end_span()

# OK
def parse_reg(p, reg, orig=None):
	tip = "Standardised text"
	if orig:
		tip += ' (original: <span class="orig">¡%s!</span>)' % html.escape(orig)
	p.start_span(klass="reg", tip=tip)
	p.add_html("⟨")
	p.dispatch_children(reg)
	p.add_html("⟩")
	p.end_span()

# TODO For now there is no nesting of <choice>, but it is allowed in some
# cases. This happens within <orig> and <reg> so must deal with it when parsing
# these tags.
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
	p.start_span(klass="space", tip=titlecase(tip))
	p.add_html(text, physical=True, logical=False, full=True)
	p.end_span()

# <abbreviations

def parse_abbr(p, node):
	p.start_span(klass="abbr", tip="Abbreviated text")
	p.dispatch_children(node)
	p.end_span()

def parse_ex(p, node):
	p.start_span(klass="abbr-expansion", tip="Abbreviation expansion")
	p.add_html("(")
	p.dispatch_children(node)
	p.add_html(")")
	p.end_span()

def parse_am(p, am):
	p.start_span(klass="abbr-mark", tip="Abbreviation mark")
	p.dispatch_children(node)
	p.end_span()

def parse_expan(p, node):
	p.dispatch_children(node)

# >abbreviations

def parse_term(p, node):
	p.dispatch_children(node)



def titlecase(s):
	if not s:
		return ""
	t = s.split(None, 1)
	t[0] = t[0].title()
	return " ".join(t)

# TODO more styling
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

# "component" is for character components like vowel markers, etc.; "character" is for akṣaras
# EGD: The EpiDoc element <gap/> ff (full section 5.4)
# EGD: "Scribal Omission without Editorial Restoration"
def parse_gap(p, gap):
	reason = gap["reason"] or "undefined" # most generic choice
	quantity = gap["quantity"]
	precision = gap["precision"]
	extent = gap["extent"] or "unknown"
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
				repl += f"{quantity}x"
			else:
				# reason = "undefined" (lost or illegible)
				repl += f"{quantity}*"
		elif unit == "character component":
			repl += quantity * "."
		else:
			repl += "%d %s %s" % (quantity, reason, config.numberize(unit, quantity))
		repl += "]"
		phys_repl = "["
		if precision == "low" and unit != "character":
			phys_repl += "ca. "
		if unit == "character":
			phys_repl += quantity * "*"
		elif unit == "character component":
			phys_repl += quantity * "."
		else:
			phys_repl += "%d %s %s" % (quantity, reason, config.numberize(unit, quantity))
		phys_repl += "]"
		tip = ""
		if precision == "low":
			tip += "About "
		tip += "%d %s %s" % (quantity, reason, config.numberize(unit, quantity))
	else:
		if unit == "character":
			repl = "[…]"
		else:
			repl = "[unknown number of %s %s]" % (reason, config.numberize(unit, +333))
		tip = "Unknown number of %s %s" % (reason, config.numberize(unit, +333))
	# <seg met="+++-++"><gap reason="lost" quantity="6" unit="character">
	# In this case, keep the tooltip, but display the meter instead of ****, etc.
	parent = gap.parent
	if parent and parent.name == "seg" and parent["met"]:
		met = parent["met"]
		if prosody.is_pattern(met):
			met = prosody.render_pattern(met)
		repl = "[%s]" % met
		phys_repl = None
	p.start_span(klass="gap", tip=tip)
	if phys_repl is not None and phys_repl != repl:
		p.add_html(html.escape(repl), plain=True, physical=False)
		p.add_html(html.escape(phys_repl), plain=True, logical=False)
	else:
		p.add_html(html.escape(repl), plain=True)
	p.end_span()
	# TODO merge consecutive values as in [ca.10x – – – ⏑ – – abc] in editorial

def parse_g_numeral(p, node):
	assert node["type"] == "numeral"
	# XXX if we have a fraction, should format it
	m = re.match(r"([0-9]+)/([0-9]+)", node.text())
	if not m:
		# No special formatting
		p.dispatch_children(node)
		return
	num, den = m.groups()
	p.add_html(f"<sup>{num}</sup>\N{fraction slash}<sub>{den}</sub>")

def parse_g(p, node):
	# <g type="...">.</g> for punctuation marks
	# <g type="...">§</g> for space fillers
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
		cat = "unclear"
	p.document.gaiji.add(t)
	info = gaiji.get(t)
	tip = f"symbol: {info['description']}"
	if cat != "unclear":
		tip = f"{cat} {tip}"
	tip = titlecase(tip)
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
def parse_unclear(p, node):
	tip = "Unclear text"
	if node["cert"] == "low":
		tip = "Very unclear text"
	reason = node["reason"]
	if reason:
		if reason == "eccentric_ductus":
			reason = f"<i>{reason}</i>"
		tip += " (%s)" % reason.replace("_", " ")
	p.start_span(klass="unclear", tip=tip)
	p.add_html("(")
	p.dispatch_children(node)
	if node["cert"] == "low":
		p.add_html("?")
	p.add_html(")")
	p.end_span()

# EGD "Editorial deletion (suppression)"
def parse_surplus(p, node):
	p.start_span(klass="surplus", tip="Superfluous text erroneously added by the scribe")
	p.add_html("{")
	p.dispatch_children(node)
	p.add_html("}")
	p.end_span()

def parse_p(p, para):
	if para["rend"] == "stanza":
		# See e.g. INSPallava06 <p rend="stanza" n="1">...
		return parse_lg(p, para)
	# Skip if we don't have anything to display (empty para, no attr).
	if not para["n"] and not para.text():
		return
	p.add_log("<para")
	if para["n"]:
		# See e.g. http://localhost:8023/display/DHARMA_INSSII0400223
		# Should be displayed like <lb/> in the edition.
		n = html.escape(para["n"])
		p.add_html(f'<span class="lb" data-tip="Line start">({n})</span>')
		p.add_html(" ")
	p.dispatch_children(para)
	p.add_log(">para")

def parse_ab(p, ab):
	p.add_log("<para")
	p.dispatch_children(ab)
	p.add_log(">para")

hi_table = {
	"italic": "i",
	"bold": "b",
	"superscript": "sup",
	"subscript": "sub",
	"check": {"klass": "check"},
	"grantha": {"klass": "grantha", "tip": "Grantha text"},
}
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
	if x <= 0 or x >= 4000:
		return str(x)
	buf = ""
	for roman, arabic in roman_table:
		while x >= arabic:
			buf += roman
			x -= arabic
	return buf

def parse_lg(p, lg):
	n = lg["n"] or "?"
	if n.isdigit():
		n = to_roman(int(n))
	met = titlecase(lg["met"])
	p.add_log("<head", level=6)
	p.add_html("%s. %s" % (n, met), plain=True)
	p.add_log(">head", level=6)
	numbered = len(lg.find("l")) > 4
	p.add_log("<verse", numbered=numbered)
	p.dispatch_children(lg)
	p.add_log(">verse")

def parse_l(p, l):
	n = l["n"] or "?"
	p.add_log("<line", n=n)
	p.dispatch_children(l)
	p.add_log(">line", n=n)

def is_description_list(nodes):
	if len(nodes) % 2:
		return False
	for i in range(0, len(nodes), 2):
		label = nodes[i]
		item = nodes[i + 1]
		if label.name != "label" or item.name != "item":
			return False
	return True

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

def extract_bib_ref(p, node):
	assert node.name == "bibl"
	ptr = node.first("ptr")
	if not ptr:
		return None, None
	target = ptr["target"]
	if not target.startswith("bib:"):
		p.complain(ptr)
		return None, None
	if target == "bib:AuthorYear_01":
		return None, None
	ref = target.removeprefix("bib:")
	loc = []
	for r in node.find("citedRange"):
		unit = r["unit"]
		if not unit or unit not in bibl_units:
			unit = "page"
		val = r.text().strip()
		if not val:
			continue
		loc.append((unit, val))
	return ref, loc

bibl_units = set(biblio.cited_range_units)

def extract_bibl_items(p, listBibl):
	recs = listBibl.find("bibl")
	ret = []
	for rec in recs:
		ref, loc = extract_bib_ref(p, rec)
		if not ref or ref == "AuthorYear_01":
			continue
		ret.append((rec, ref, loc))
	return ret

def parse_label(p, label):
	pass # We deal with this in other handlers

def parse_listBibl(p, node):
	recs = extract_bibl_items(p, node)
	# Avoid displaying "Primary" or "Secondary" if there is nothing there.
	if not recs:
		return
	typ = node["type"]
	if typ:
		p.add_log("<head")
		p.add_text(titlecase(typ))
		p.add_log(">head")
	for rec, ref, loc in recs:
		p.add_code("bib", ref, loc=loc, n=rec["n"])

def parse_bibl(p, node):
	rend = node["rend"]
	if rend not in ("omitname", "ibid", "default"):
		rend = "default"
	ref, loc = extract_bib_ref(p, node)
	if not ref:
		return
	p.add_code("ref", ref, rend=rend, loc=loc, missing=ref not in p.document.biblio)

def parse_body(p, body):
	for elem in body.children():
		p.dispatch(elem)

def parse_title(p, title):
	p.dispatch_children(title)

def parse_q(p, q):
	if q["rend"] == "block": # TODO other usual values for @rend?
		p.add_log("<blockquote")
		p.dispatch_children(q)
		p.add_log(">blockquote")
	else:
		p.add_html("“")
		p.dispatch_children(q)
		p.add_html("”")

def parse_quote(p, quote):
	return parse_q(p, quote)

def parse_cit(p, cit):
	# <cit>
	#    <quote>the text</quote>
	#    <bibl><ptr target="bib:Agrawala1983_01"/></bibl>
	# </cit>
	#
	# "the text" (Agrawala 1983)
	q = cit.first("quote")
	block = False
	if q and q["rend"] == "block":
		block = True
	if block:
		p.add_log("<blockquote")
	for node in cit.children():
		if node.name == "bibl":
			p.add_text(" (")
			p.dispatch(node)
			p.add_text(")")
		elif node.name == "quote" and block:
			p.dispatch_children(node)
	if block:
		p.add_log(">blockquote")

def gather_people(stmt, *paths):
	nodes = [node for path in paths for node in stmt.find(path)]
	nodes.sort(key=lambda node: node.location.start)
	full_names = []
	dharma_ids = []
	for node in nodes:
		ident = node["ref"]
		# XXX always use the indent here, don't resolve it. but what if
		# we don't have any? for now use two fields: one where we list
		# all full names, and another where we list only people who
		# have a dharma id, viz. the "real" dharma editors.
		if ident and ident.startswith("part:"):
			if ident == "part:jodo": # John Doe, placeholder
				continue
			ident = ident.removeprefix("part:")
			name = people.plain(ident)
			if not name:
				continue # XXX keep the id in this case?
			config.append_unique(dharma_ids, ident)
		else:
			name = config.normalize_space(node.text(space="preserve"))
			if not name:
				continue
		config.append_unique(full_names, name)
	return full_names, dharma_ids

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

def parse_publicationStmt(p, stmt):
	pass
	# TODO extract the pub place

def parse_roleName(p, node):
	p.dispatch_children(node)

def parse_placeName(p, node):
	p.dispatch_children(node)

def parse_persName(p, node):
	p.dispatch_children(node)

def parse_measure(p, node):
	p.dispatch_children(node)

def parse_date(p, node):
	p.dispatch_children(node)

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

def parse_facsimile(p, node):
	pass # for images, will see later on

def parse_fileDesc(p, node):
	p.dispatch_children(node)

def parse_teiHeader(p, node):
	p.dispatch_children(node)

def parse_text(p, node):
	p.dispatch_children(node)

def parse_TEI(p, node):
	p.dispatch_children(node)

def make_handlers_map():
	ret = {}
	for name, obj in copy.copy(globals()).items():
		if not name.startswith("parse_"):
			continue
		name = name.removeprefix("parse_")
		ret[name] = obj
	return ret

HANDLERS = make_handlers_map()
