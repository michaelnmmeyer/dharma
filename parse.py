import os, sys, re, io, copy, html, unicodedata, functools
from urllib.parse import urlparse
from dharma import prosody, people, tree, gaiji, config, unicode, biblio
from dharma import langs, document
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

@handler("lem")
def parse_lem(p, lem):
	p.dispatch_children(lem)
	add_lemmas_links(p, lem["source"])

@handler("ptr")
def parse_ptr(p, ptr):
	ref = ptr["target"]
	if not ref.startswith("bib:"):
		return
	ref = ref.removeprefix("bib:")
	print("have ", p.document.sigla.get(ref))
	kwargs = {
		"rend": "default",
		"loc": [],
		"missing": ref not in p.document.biblio,
		"siglum": p.document.sigla.get(ref),
	}
	p.add_code("ref", ref, **kwargs)

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
		p.add_html(f'</a>')

def add_lemmas_links(p, sources):
	if not sources:
		return
	sources = [source.removeprefix("bib:") for source in sources.split()]
	for ref in sources:
		p.add_text(" ")
		siglum = p.document.sigla.get(ref)
		p.add_code("ref", ref, rend="default", loc=[], siglum=siglum, missing=ref not in p.document.biblio)

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

@handler("num")
def parse_num(p, num):
	# TODO for now we don't deal with @atLeast and @atMost
	if num["value"] and num.text() != num["value"]:
		p.start_span(klass="num", tip=f"Numeral {num['value']}")
		p.dispatch_children(num)
		p.end_span()
	else:
		p.start_span(klass="num")
		p.dispatch_children(num)
		p.end_span()

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
@handler("supplied")
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
@handler("add")
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
@handler("del")
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
@handler("subst")
def parse_subst(p, subst):
	# (del, add)
	# Use the text of <add> for search
	p.dispatch_children(subst)

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

def milestone_unit_type(milestone):
	unit = milestone["unit"] or "column"
	typ = milestone["type"]
	if typ not in ("pagelike", "gridlike"):
		typ = "gridlike"
	return unit, typ

@handler("milestone")
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

@handler("lb")
def parse_lb(p, elem):
	n = milestone_n(p, elem)
	brk = milestone_break(elem)
	# On alignment, EGD §7.5.2
	m = re.match(r"^text-align:\s?(right|center|left|justify)$", elem["style"])
	if m:
		align = m.group(1)
	else:
		align = "left"
	p.add_phys("line", n=n, brk=brk)

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
		fw = elem.next
		if not fw or not fw.name == "fw":
			break
		fws.append(fw)
		elem = fw
	# XXX should mark fws as visited, so that a misplaced fw is
	# still displayed by parse_fw. idem for <head> and such.
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
			p.add_html("(", logical=False, physical=False, full=True)
			p.add_text(f"{place}: ")
			p.start_span(klass="fw-contents")
			p.dispatch_children(fw)
			p.end_span()
			p.add_html(")", logical=False, physical=False, full=True)
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
@handler("corr")
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
@handler("orig")
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
@handler("reg")
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
	p.start_span(klass="space", tip=titlecase(tip))
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
	p.dispatch_children(node)
	p.end_span()

@handler("expan")
def parse_expan(p, node):
	p.dispatch_children(node)

# >abbreviations

@handler("term")
def parse_term(p, node):
	p.dispatch_children(node)



def titlecase(s): # XXX just a capital to the first letter, should rename the func to "sentence"
	if not s:
		return ""
	t = s.split(None, 1)
	t[0] = t[0].capitalize()
	return " ".join(t)

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

# "component" is for character components like vowel markers, etc.; "character" is for akṣaras
# EGD: The EpiDoc element <gap/> ff (full section 5.4)
# EGD: "Scribal Omission without Editorial Restoration"
@handler("gap")
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
				repl += f"{quantity}×"
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
	if isinstance(parent, tree.Tag) and parent.name == "seg" and parent["met"]:
		met = parent["met"]
		if prosody.is_pattern(met):
			met = prosody.render_pattern(met)
		repl = "[%s]" % met
		phys_repl = None
	p.start_span(klass="gap", tip=tip)
	if phys_repl is not None and phys_repl != repl:
		p.add_html(html.escape(repl), plain=True, physical=False)
		p.add_html(html.escape(phys_repl), plain=True, logical=False, full=False)
	else:
		p.add_html(html.escape(repl), plain=True)
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
@handler("unclear")
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
@handler("surplus")
def parse_surplus(p, node):
	p.start_span(klass="surplus", tip="Superfluous text erroneously added by the scribe")
	p.add_html("{")
	p.dispatch_children(node)
	p.add_html("}")
	p.end_span()

@handler("p")
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

@handler("ab")
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
	if x <= 0 or x >= 4000:
		return str(x)
	buf = ""
	for roman, arabic in roman_table:
		while x >= arabic:
			buf += roman
			x -= arabic
	return buf

@handler("lg")
def parse_lg(p, lg):
	n = lg["n"] or "?"
	if n.isdigit():
		n = to_roman(int(n))
	met = lg["met"]
	if prosody.is_pattern(met):
		met = prosody.render_pattern(met)
	else:
		met = titlecase(met)
	p.add_log("<head", level=6)
	p.add_html(f"{n}. {met}", plain=True)
	p.add_log(">head", level=6)
	numbered = len(lg.find("l")) > 4
	p.add_log("<verse", numbered=numbered)
	p.dispatch_children(lg)
	p.add_log(">verse")

@handler("l")
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
	recs = listBibl.find("bibl")
	ret = []
	for rec in recs:
		ref, loc = extract_bib_ref(rec)
		if not ref or ref == "AuthorYear_01":
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
		p.add_text(titlecase(typ))
		p.add_log(">head")
	for rec, ref, loc in recs:
		p.add_code("bib", ref, loc=loc, n=rec["n"])

@handler("bibl")
def parse_bibl(p, node):
	rend = node["rend"]
	if rend not in ("omitname", "ibid", "default"):
		rend = "default"
	ref, loc = extract_bib_ref(node)
	if not ref:
		return
	p.add_code("ref", ref, rend=rend, loc=loc, missing=ref not in p.document.biblio)

@handler("title")
def parse_title(p, title):
	p.dispatch_children(title)

@handler("q")
def parse_q(p, q):
	if q["rend"] == "block": # TODO other usual values for @rend?
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

@handler("publicationStmt")
def parse_publicationStmt(p, stmt):
	pass
	# TODO extract the pub place

@handler("roleName")
def parse_roleName(p, node):
	p.dispatch_children(node)

@handler("placeName")
def parse_placeName(p, node):
	p.dispatch_children(node)

@handler("persName")
def parse_persName(p, node):
	p.dispatch_children(node)

@handler("measure")
def parse_measure(p, node):
	p.dispatch_children(node)

@handler("date")
def parse_date(p, node):
	p.dispatch_children(node)

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

@handler("facsimile")
def parse_facsimile(p, node):
	pass # for images, will see later on

@handler("fileDesc")
def parse_fileDesc(p, node):
	p.dispatch_children(node)

@handler("teiHeader")
def parse_teiHeader(p, node):
	p.dispatch_children(node)

@handler("text")
def parse_text(p, node):
	p.dispatch_children(node)

@handler("TEI")
def parse_TEI(p, node):
	p.dispatch_children(node)

# Within inscriptions, <div> shouldn't nest, except that we can have
# <div type="textpart"> within <div type="edition">.
# All the DHARMA_INSEC* stuff don't follow the ins schema, too different.
@handler("div")
def parse_div(p, div):
	if div["type"] != "textpart":
		p.complain(div)
		return
	n = milestone_n(p, div)
	# rend style subtype
	children = div.children()
	i = 0
	# <head> is supposed to only occur in this context in inscriptions, but
	# in fact we don't really care, might allow it somewhere else
	p.start_div(n=n)
	if children and children[0].name == "head":
		p.add_log("<head")
		p.add_text(n)
		p.add_text(". ")
		p.dispatch_children(children[0])
		p.add_log(">head")
		i += 1
	for child in children[i:]:
		p.dispatch(child)
	p.end_div()

def gather_sections(p, div):
	p.push(div["type"])
	for child in div:
		if isinstance(child, tree.Tag) and child.name == "div":
			if p.within_div:
				p.end_div()
			p.dispatch(child)
		elif not isinstance(child, (tree.Comment, tree.Instruction)):
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
	trans = gather_sections(p, div)
	if not trans:
		return
	title = "Translation"
	lang = div["lang"]
	if lang:
		lang = html.escape(langs.from_code(lang) or lang)
		title += f" into {lang}"
	resp = div["resp"]
	if resp:
		title += " by "
		resps = resp.split()
		for i, resp in enumerate(resps):
			if i == 0:
				pass
			elif i < len(resps) - 1:
				title += ", "
			else:
				title += " and "
			title += fetch_resp(resp)
	source = div["source"]
	if source:
		ref = source.removeprefix("bib:")
		source = biblio.get_ref(ref, missing=ref not in p.document.biblio, rend="default", loc="")
		title += f" by {source}"
	trans.title = title
	return trans

def gather_biblio(p, body):
	for bibl in body.find("//listBibl/bibl"):
		siglum = bibl["n"]
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

@handler("body")
def parse_body(p, body):
	gather_biblio(p, body)
	for div in body.children():
		type = div["type"]
		if not div.name == "div" or not type in ("edition", "translation", "commentary", "bibliography", "apparatus"):
			p.complain(div)
			continue
		p.divs.clear()
		p.divs.append(set())
		if type == "edition":
			if "lang" in div.attrs:
				config.append_unique(p.document.edition_main_langs, div["lang"])
			else:
				for textpart in div.find("//div"):
					if not textpart["type"] == "textpart":
						continue
					if not "lang" in textpart.attrs:
						continue
					config.append_unique(p.document.edition_main_langs, textpart["lang"])
			# XXX Add sec. languages https://github.com/erc-dharma/project-documentation/issues/250
			#and add validity check (in schema?)
			edition = gather_sections(p, div)
			if edition:
				p.document.edition = edition
		elif type == "apparatus":
			p.document.apparatus = gather_sections(p, div)
		elif type == "translation":
			trans = process_translation(p, div)
			if trans:
				p.document.translation.append(trans)
		elif type == "commentary":
			p.document.commentary = gather_sections(p, div)
		elif type == "bibliography":
			p.document.bibliography = gather_sections(p, div)
		else:
			assert 0

def process_file(path, data):
	t = tree.parse_string(data, path=path)
	f = t.first("//teiHeader/encodingDesc")
	if f:
		f.delete()
	f = t.first("//teiHeader/revisionDesc")
	if f:
		f.delete()
	f = t.first("//publicationStmt")
	if f:
		f.delete()
	p = Parser(t)
	p.dispatch(p.tree.root)
	body = t.first("//body")
	if body:
		p.document.xml = tree.html_format(t)
	db = config.db("texts")
	langs = set()
	for node in t.find("//*"):
		if not "lang" in node.attrs:
			continue
		lang = node["lang"]
		(code,) = db.execute("select id from langs_by_code where code = ?", (lang,)).fetchone() or ("und",)
		langs.add(code)
	if not langs:
		langs.add("und")
	p.document.langs = sorted(langs)
	return p.document

def export_plain():
	db = config.db("texts")
	renderer = document.PlainRenderer(strip_physical=True)
	out_dir = config.path_of("plain")
	os.makedirs(out_dir, exist_ok=True)
	for name, path, data in db.execute("""
		select name, printf('%s/%s/%s', ?, repo, path), data
		from documents natural join files where name glob 'DHARMA_INS*'
		""", (config.path_of("repos"),)):
		print(path)
		try:
			ret = renderer.render(process_file(path, data))
		except tree.Error:
			continue
		out_file = os.path.join(out_dir, name + ".txt")
		with open(out_file, "w") as f:
			f.write(ret)

if __name__ == "__main__":
	db = config.db("texts")
	db.execute("begin")
	path = sys.argv[1]
	data = open(path, "rb").read()
	try:
		doc = process_file(path, data)
		print(doc.apparatus)
	except BrokenPipeError:
		pass
	db.execute("end")
