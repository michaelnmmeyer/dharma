# I initially wanted to do validation and display together, with a real parser,
# possibly bound to rng. But in practice, we need to generate a useful display
# even when texts are not valid. So many files are invalid that being too
# strict would leave us with not much, and even so not being able to display a
# text at all because of a single error would be super annoying.
#
# to make sure we examine everything and to signal stuff we haven't taken into
# account, might want to add a "visited" flag to @. maybe id. for text nodes.

# TODO for tips use https://stackoverflow.com/questions/2597773/how-do-i-put-a-div-box-around-my-cursor-on-click

import os, sys, re, io, copy, html, unicodedata
from dharma import prosody, people, tree, gaiji, config, grapheme, biblio
from dharma import tree as etree

write = sys.stdout.write

force_color = True
def term_color(code=None):
	if not os.isatty(1) and not force_color:
		return
	if not code:
		write("\N{ESC}[0m")
		return
	code = code.lstrip("#")
	assert len(code) == 6
	R = int(code[0:2], 16)
	G = int(code[2:4], 16)
	B = int(code[4:6], 16)
	write(f"\N{ESC}[38;2;{R};{G};{B}m")

def term_html(): term_color("#5f00ff")
def term_bib(): term_color("#aa007f")
def term_log(): term_color("#008700")
def term_phys(): term_color("#0055ff")
def term_text(): term_color("#aa007f")
def term_span(): term_color("#b15300")
def term_reset(): term_color()

def write_debug(t, data, **params):
	if t == "html":
		term_html()
	elif t == "log":
		term_log()
	elif t == "phys":
		term_phys()
	elif t == "text":
		term_text()
	elif t == "span":
		term_span()
	elif t == "bib" or t == "ref":
		term_bib()
	else:
		assert 0, t
	write("%-04s" % t)
	if data:
		if t in ("text", "html"):
			write(" %r" % data)
		else:
			write(" %s" % data)
	if params:
		for k, v in sorted(params.items()):
			write(" :%s %r" % (k, v))
	term_reset()
	write("\n")

PARA_SEP = chr(1)

def normalize(s):
	if s is None:
		s = ""
	elif not isinstance(s, str):
		# make sure matching doesn't work across array elements
		s = "!!!!!".join(s)
	s = unicodedata.normalize("NFKD", s)
	s = "".join(c for c in s if not unicodedata.combining(c))
	s = s.casefold()
	s = s.replace("œ", "oe").replace("æ", "ae").replace("ß", "ss").replace("đ", "d")
	return unicodedata.normalize("NFC", s.strip())

class Block:

	def __init__(self, name=""):
		self.name = name
		self.code = []
		self.finished = False

	def __repr__(self):
		return "<Block(%s) %r>" % (self.name, self.code)

	def empty(self):
		for cmd, data, params in self.code:
			if cmd == "text" and data == " ":
				continue
			return False
		return True

	def __bool__(self):
		return not self.empty()

	def start_item(self):
		if any(cmd == "text" for cmd, _, _ in self.code):
			self.add_text(PARA_SEP)

	def add_text(self, data):
		if not data:
			return
		data = re.sub(r"\s+", " ", data)
		return self.add_code("text", data)

	def add_html(self, data):
		return self.add_code("html", data)

	def close_line(self, brk):
		i = len(self.code)
		p = i
		while i > 0:
			i -= 1
			rcmd, rdata, rparams = self.code[i]
			if rcmd == "log" and rdata == ">div":
				p = i
				continue
			if rcmd != "phys":
				continue
			if rdata.startswith("="):
				p = i
				continue
			if rdata == "<line":
				self.code.insert(p, ("phys", ">line", {"brk": brk}))
				break

	def add_phys(self, data, **params):
		# XXX handle breaks consistently,trim space always?
		if data != "line":
			assert data.startswith("=")
			self.add_code("phys", data, **params)
			return
		brk = params["brk"]
		self.close_line(brk)
		if not brk:
			i = len(self.code)
			while i > 0:
				i -= 1
				rcmd, rdata, rparams = self.code[i]
				if rcmd == "span" and data == "<" and "dh-space" in rparams["klass"]:
					break
				if rcmd != "text":
					continue
				rdata = rdata.rstrip()
				if not rdata:
					del self.code[i]
					continue
				self.code[i] = (rcmd, rdata, rparams)
				break
		self.add_code("phys", "<line", **params)

	def add_log(self, data, **params):
		self.add_code("log", data, **params)

	def start_span(self, **params):
		assert not "n" in params
		params["n"] = 1
		params["klass"] = [params["klass"]]
		params["tip"] = [params["tip"]]
		i = len(self.code)
		while i > 0:
			i -= 1
			rcmd, rdata, rparams = self.code[i]
			if rcmd != "span":
				continue
			if rdata == "<":
				rparams["n"] += params["n"]
				rparams["klass"] += params["klass"]
				rparams["tip"] += params["tip"]
				return
			assert rdata == ">"
			break
		self.add_code("span", "<", **params)

	def end_span(self):
		i = len(self.code)
		while i > 0:
			i -= 1
			rcmd, rdata, rparams = self.code[i]
			if rcmd != "span":
				continue
			assert rdata == "<"
			assert rparams["n"] > 0
			rparams["n"] -= 1
			if rparams["n"] > 0:
				return
			break
		self.add_code("span", ">")

	def add_code(self, t, data=None, **params):
		rec = (t, data, params)
		self.code.append(rec)

	def finish(self):
		self.close_line(True)
		self.finished = True

	def render_common(self, buf, t, data, params):
		if t == "text":
			# TODO be more accurate, only need to hyphenate Indic
			# languages
			if self.name == "edition":
				data = grapheme.hyphenate(data)
			text = html.escape(data)
			buf.append(text)
		elif t == "html":
			buf.append(data)
		elif t == "span":
			if data == "<":
				klasses = " ".join(params["klass"])
				tip = " | ".join(params["tip"])
				buf.append('<span class="%s dh-tipped"><span class="dh-tip">%s</span>' % (html.escape(klasses), html.escape(tip)))
			elif data == ">":
				buf.append('</span>')
			else:
				assert 0, data
		elif t == "bib":
			key, rec = biblio.get_entry(data, params)
			if key:
				buf.append(f'<p class="dh-bib-entry" id="dh-bib-key-{key}">{rec}</p>')
			else:
				buf.append(f'<p class="dh-bib-entry dh-bib-ref-invalid dh-tipped"><span class="dh-tip">Invalid bibliographic reference</span>{rec}</p>')
		elif t == "ref":
			key, ref, loc = biblio.get_ref(data, **params)
			siglum = params.get("siglum")
			if key:
				buf.append(f'<span class="dh-bib-ref">')
			else:
				buf.append(f'<span class="dh-bib-ref-invalid dh-tipped"><span class="dh-tip">Invalid bibliographic reference</span>')
			if key:
				buf.append(f'<a href="#dh-bib-key-{key}">')
			if siglum:
				buf.append(html.escape(siglum))
			else:
				buf.append(ref)
			if key:
				buf.append('</a>')
			if loc:
				buf.append(loc)
			buf.append('</span>')
		else:
			assert 0, t

	def render_logical(self):
		assert self.finished
		buf = []
		for t, data, params in self.code:
			if t == "log":
				if data == "<div":
					buf.append('<div class="dh-ed-section">')
				elif data == ">div":
					buf.append('</div>')
				elif data == "<head":
					lvl = params.get("level", 3)
					buf.append('<h%d class="dh-ed-heading">' % lvl)
				elif data == ">head":
					lvl = params.get("level", 3)
					buf.append('</h%d>' % lvl)
				elif data == "<para" or data == "<line":
					buf.append("<p>")
				elif data == ">para" or data == ">line":
					buf.append("</p>")
				elif data == "<verse":
					buf.append('<div class="dh-verse">')
				elif data == ">verse":
					buf.append('</div>')
				elif data == "<list":
					typ = params["type"]
					if typ == "plain":
						buf.append('<ul class="dh-list-plain">')
					elif typ == "bulleted":
						buf.append('<ul>')
					elif typ == "numbered":
						buf.append('<ol>')
					elif typ == "description":
						buf.append('<dl>')
					else:
						assert 0
				elif data == ">list":
					typ = params["type"]
					if typ == "plain":
						buf.append('</ul>')
					elif typ == "bulleted":
						buf.append('</ul>')
					elif typ == "numbered":
						buf.append('</ol>')
					elif typ == "description":
						buf.append('</dl>')
					else:
						assert 0
				elif data == "<item":
					buf.append('<li>')
				elif data == ">item":
					buf.append('</li>')
				elif data == "<key":
					buf.append('<dt>')
				elif data == ">key":
					buf.append('</dt>')
				elif data == "<value":
					buf.append('<dd>')
				elif data == ">value":
					buf.append('</dd>')
				else:
					assert 0, data
			elif t == "phys":
				if data == "<line":
					buf.append('<span class="dh-lb dh-tipped"><span class="dh-tip">Line start</span>(%s)</span>' % html.escape(params["n"]))
					if params["brk"]:
						buf.append(" ")
				elif data == ">line":
					pass
				elif data == "=page":
					buf.append('<span class="dh-pagelike dh-tipped"><span class="dh-tip">Page start</span>(\N{next page} %s)</span>' % html.escape(params["n"]))
				elif data.startswith("=") and params["type"] == "pagelike":
					unit = html.escape(data[1:].title())
					n = html.escape(params["n"])
					buf.append(f'<span class="dh-pagelike dh-tipped"><span class="dh-tip">{unit} start</span>({unit} {n})</span>')
				elif data.startswith("=") and params["type"] == "gridlike":
					unit = html.escape(data[1:].title())
					n = html.escape(params["n"])
					buf.append(f'<span class="dh-gridlike dh-tipped"><span class="dh-tip">{unit} start</span>({unit} {n})</span>')
				else:
					assert 0, data
			else:
				self.render_common(buf, t, data, params)
		return "".join(buf)

	def render_physical(self):
		assert self.finished
		buf = []
		for t, data, params in self.code:
			if t == "phys":
				if data == "<line":
					buf.append('<p class="dh-line"><span class="dh-lb dh-tipped"><span class="dh-tip">Line start</span>(%s)</span> ' % html.escape(params["n"]))
				elif data == ">line":
					if not params["brk"]:
						buf.append('<span class="dh-hyphen-break dh-tipped"><span class="dh-tip">Hyphen break</span>-</span>')
					buf.append('</p>')
				elif data == "=page":
					buf.append('<span class="dh-pagelike dh-tipped"><span class="dh-tip">Page start</span>(\N{next page} %s)</span> ' % html.escape(params["n"]))
				elif data.startswith("=") and params["type"] == "pagelike":
					unit = html.escape(data[1:].title())
					buf.append('<span class="dh-pagelike dh-tipped"><span class="dh-tip">%s start</span>(%s %s)</span>' % (unit, unit, html.escape(params["n"])))
				elif data.startswith("=") and params["type"] == "gridlike":
					unit = html.escape(data[1:].title())
					buf.append('<span class="dh-gridlike dh-tipped"><span class="dh-tip">%s start</span>(%s %s)</span>' % (unit, unit, html.escape(params["n"])))
				else:
					assert 0, data
			elif t == "log":
				if data == "<div":
					buf.append('<div class="dh-ed-section">')
				elif data == ">div":
					buf.append('</div>')
				elif data == "<head" and not params.get("level"):
					buf.append('<h3 class="dh-ed-heading">')
				elif data == ">head" and not params.get("level"):
					buf.append('</h3>')
			else:
				self.render_common(buf, t, data, params)
		return "".join(buf)

	def searchable_text(self):
		assert self.finished
		buf = []
		for t, data, _ in self.code:
			if not t == "text":
				continue
			buf.append(data)
		return normalize("".join(buf))

class Document:

	tree = None # tree.Tree

	repository = ""
	ident = ""
	title = None
	author = None
	editors = None
	langs = None
	summary = None

	edition = None
	apparatus = None
	# we can have several translations e.g. DHARMA_INSPallava00002
	translation = None
	commentary = None
	bibliography = None

	xml = ""

	def __init__(self):
		self.langs = []
		self.translation = []
		self.sigla = {}

class Parser:

	tree = None
	div_level = 0

	# For HTML output
	heading_shift = 1

	def __init__(self, tree, handlers):
		self.tree = tree
		self.document = Document()
		self.document.ident = os.path.basename(os.path.splitext(tree.path)[0])
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
		if n != "?" and n in self.divs[-1]:
			return False
		self.divs[-1].add(n)
		return True

	def start_div(self, n="?"):
		# we could duplicate <div in log and phys, for commodity
		self.add_log("<div", n=n)
		self.divs.append(set())

	def end_div(self):
		assert self.within_div
		self.divs.pop()
		self.add_log(">div")

	def add_text(self, text):
		return self.blocks[-1].add_text(text)

	def add_html(self, data):
		return self.blocks[-1].add_html(data)

	def add_phys(self, data, **params):
		return self.blocks[-1].add_phys(data, **params)

	def add_code(self, t, data=None, **params):
		return self.blocks[-1].add_code(t, data, **params)

	def add_log(self, data, **params):
		return self.blocks[-1].add_log(data, **params)

	def start_item(self):
		return self.blocks[-1].start_item()

	def start_span(self, **params):
		return self.blocks[-1].start_span(**params)

	def end_span(self):
		return self.blocks[-1].end_span()

	shorthands = {
		"_": etree.parse_string('<space/>'),
		"|": etree.parse_string('<g type="danda">.</g>'),
		"/": etree.parse_string('<g type="dandaOrnate">.</g>'),
		"||": etree.parse_string('<g type="ddanda">.</g>'),
		"//": etree.parse_string('<g type="ddandaOrnate">.</g>'),
		"@": etree.parse_string('<g type="circle">.</g>'),
		"~": etree.parse_string('<g type="dash">.</g>'),
		# the transliteration shorthand , is recommended for <g type="comma">.</g>
		# yeah but too ambiguous
	}
	shorthands_re = re.compile("(%s)" % "|".join(re.escape(s) for s in sorted(shorthands, key=len, reverse=True)))

	def split_string(self, s):
		for chunk in self.shorthands_re.split(s):
			t = self.shorthands.get(chunk)
			if t:
				self.dispatch(t.root)
			else:
				self.add_text(chunk.replace("'", "’"))

	def dispatch(self, node):
		if node.type in ("comment", "instruction"):
			return
		if node.type == "string":
			self.split_string(str(node))
			return
		assert node.type == "tag"
		f = self.handlers.get(node.name)
		if not f:
			self.complain("no handler for %r, ignoring it" % node)
			return
		try:
			f(self, node)
		except tree.Error as e:
			self.complain(e)

	def dispatch_children(self, node):
		for child in node:
			self.dispatch(child)

	def complain(self, msg):
		#print("? %s" % msg)
		pass

# Like the eponymous function in xslt
def normalize_space(s):
	s = s.strip()
	return re.sub(r"\s+", " ", s)

def parse_lem(p, lem):
	p.dispatch_children(lem)

def parse_ptr(p, ptr):
	target = ptr["target"]
	if not target.startswith("bib:"):
		return
	target = target.removeprefix("bib:")
	p.add_code("ref", target, rend="default", loc=[])

def parse_ref(p, ref):
	# TODO
	p.dispatch_children(ref)

def parse_rdg(p, rdg):
	p.start_span(klass="dh-reading", tip="Reading")
	p.dispatch_children(rdg)
	p.end_span()
	sources = [source.removeprefix("bib:") for source in rdg["source"].split()]
	if sources:
		for source in sources:
			p.add_text(" ")
			siglum = p.document.sigla.get(source)
			p.add_code("ref", source, rend="default", loc=[], siglum=siglum)

def parse_app(p, app):
	loc = app["loc"] or "?"
	p.start_span(klass="dh-lb", tip="Line number")
	p.add_text("(%s)" % loc)
	p.end_span()
	p.add_text(" ")
	lem = app.first("lem")
	if lem:
		p.dispatch(lem)
	rdgs = app.find("rdg")
	if rdgs:
		p.add_text(" ◇ ")
	notes = app.find("note")
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
	"undefined": ("[]", "Lost or omitted text")
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
	p.start_span(klass="dh-supplied", tip=tip)
	if seps:
		p.add_html(seps[0])
	p.dispatch_children(supplied)
	if seps:
		p.add_html(seps[1])
	p.end_span()

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

def parse_milestone(p, milestone):
	n = milestone_n(p, milestone)
	brk = milestone_break(milestone)
	unit = milestone["unit"]
	if unit not in milestone_units:
		unit = "column"
	typ = milestone["type"]
	if not typ in ("pagelike", "gridlike"):
		typ = "gridlike"
	p.add_phys("=" + unit, type=typ, n=n, brk=brk)

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
	pass # we deal with it within <pb>

def parse_pb(p, elem):
	n = milestone_n(p, elem)
	brk = milestone_break(elem)
	fw = elem.next
	if fw and fw.name == "fw":
		place = fw["place"]
	else:
		place = ""
	p.add_phys("=page", n=n, brk=brk)
	#p.dispatch_children(fw) TODO

# >milestones

# <editorial

# OK
def parse_sic(p, sic):
	p.start_span(klass="dh-sic", tip="Incorrect text")
	p.add_html("¿")
	p.dispatch_children(sic)
	p.add_html("?")
	p.end_span()

# OK
def parse_corr(p, corr):
	p.start_span(klass="dh-corr", tip="Corrected text")
	p.add_html('⟨')
	p.dispatch_children(corr)
	p.add_html('⟩')
	p.end_span()

# OK
def parse_orig(p, orig):
	p.start_span(klass="dh-orig", tip="Non-standard text")
	p.add_html("¡")
	p.dispatch_children(orig)
	p.add_html("!")
	p.end_span()

# OK
def parse_reg(p, reg):
	p.start_span(klass="dh-reg", tip="Standardised text")
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
		# In this case for search just keep the text of the 1st unclear.
		p.start_span(klass="dh-choice-unclear", tip="Unclear (several possible readings)")
		p.add_html("(")
		sep = ""
		for child in children:
			p.add_html(sep)
			sep = "/"
			p.dispatch_children(child)
		p.add_html(")")
		p.end_span()
	else:
		# <choice><sic>...</sic><corr>...</corr></choice>
		# OR
		# <choice><orig>...</orig><reg>...</reg></choice>
		#
		# For searching keep <corr> and <reg>, ignore the rest.
		p.dispatch_children(node) # nothing special to do

# >editorial

# Valid cases are:
#
#	<space [type="semantic"]/> (shorthand is '_')
#	<space [type="semantic"] quantity=... unit="characters"/>
#	<space type="vacat" quantity=... unit="characters"/>
#	<space type="(binding-hole|descender|ascender|defect|feature)"/>
#	<space type="unclassified"/>
#	<space type="unclassified" quantity=... unit="characters"/>
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
			s = "small space (from barely noticeable to less than two average character widths in extent)"
		else:
			s = f"large space (about {quant} {unit}s wide)"
		tip = "%s; %s" % (s, tip)
		text *= quant
	p.start_span(klass="dh-space", tip=titlecase(tip))
	p.add_html(text)
	p.end_span()

def parse_abbr(p, node):
	p.start_span(klass="dh-abbr", tip="Abbreviated text")
	p.dispatch_children(node)
	p.end_span()

def parse_ex(p, node):
	p.start_span(klass="dh-abbr-expansion", tip="Abbreviation expansion")
	p.add_html("(")
	p.dispatch_children(node)
	p.add_html(")")
	p.end_span()

def parse_expan(p, node):
	p.dispatch_children(node)

def parse_term(p, node):
	p.dispatch_children(node)

def parse_add(p, node):
	p.start_span(klass="dh-add", tip="Scribal addition")
	p.add_html("⟨⟨")
	p.dispatch_children(node)
	p.add_html("⟩⟩")
	p.end_span()

def parse_del(p, node):
	p.start_span(klass="dh-del", tip="Scribal deletion")
	p.add_html("⟦")
	p.dispatch_children(node)
	p.add_html("⟧")
	p.end_span()

def numberize(s, n):
	last_word = s.split()[-1].lower()
	if last_word not in ("character", "component", "line", "page", "editor"):
		print("cannot numberize term %r" % last_word, file=sys.stderr)
		return s
	if n == 1:
		return s
	return s + "s"

def titlecase(s):
	t = s.split(None, 1)
	t[0] = t[0].title()
	return " ".join(t)

def parse_seg(p, seg):
	if seg.first("gap"):
		# We deal with this within parse_gap
		p.dispatch_children(seg)
		return
	# TODO

"""
Legit values for @reason:
  10755 lost
   6136 illegible
   1469 undefined
    290 ellipsis
     38 omitted

Legit values for @unit
  13717 character
   1208 component
    263 line
     11 page
     + plate
     + folio

@quantity must be an integer

each <gap unit="component"> is supposed to always be wrapped in a <seg
type="component" subtype=...>. We don't have that in practice: 105 cases where
parent is not <seg>. (but a <seg type="component"> doesn't necessarily hold a
<gap>.)



<seg type="component" subtype="body"><gap reason="lost" quantity="1" unit="component"/></seg>
"""
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
		p.add_html("\N{horizontal ellipsis}")
		return
	if reason == "undefined":
		reason = "lost or illegible"
	child = gap.first("certainty")
	if child and child["match"] == ".." and child["locus"] == "name":
		reason = "possibly %s" % reason
	if unit == "component":
		unit = "character component"
	if quantity.isdigit():
		quantity = int(quantity)
		repl = "["
		if precision == "low":
			repl += "ca. "
		if unit == "character":
			repl += quantity * "*" + "]"
		else:
			repl += "%d %s %s]" % (quantity, reason, numberize(unit, quantity))
		tip = ""
		if precision == "low":
			tip += "About "
		tip += "%d %s %s" % (quantity, reason, numberize(unit, quantity))
	else:
		if unit == "character":
			repl = "[…]"
		else:
			repl = "[unknown number of %s %s]" % (reason, numberize(unit, +333))
		tip = "Unknown number of %s %s" % (reason, numberize(unit, +333))
	parent = gap.parent
	if parent and parent.name == "seg" and parent["met"]:
		met = parent["met"]
		if prosody.is_pattern(met):
			met = prosody.render_pattern(met)
		repl = "[%s]" % met
	p.start_span(klass="dh-gap", tip=tip)
	p.add_html(html.escape(repl))
	p.end_span()
	# TODO restart [ca.10x – – – ⏑ – – abc] in editorial
	# <seg met="+++-++">

def parse_g(p, node):
	# <g type="...">.</g> for punctuation marks
	# <g type="...">§</g> for space fillers
	# <g type="..."></g> in the other cases viz. for symbols whose functions is unclear
	# The guide talks about subtype, but
	t = node["type"] or "symbol"
	if t == "numeral":
		return p.dispatch_children(node)
	text = node.text()
	if text == ".":
		cat = "punctuation"
	elif text == "§":
		cat = "space-filler"
	else:
		cat = "unclear"
	st = node["subtype"]
	if t == "symbol" and st:
		t = st
	info = gaiji.get(t)
	tip = titlecase(info["description"])
	tip = "%s (category: %s)" % (tip, cat)
	p.start_span(klass="dh-symbol", tip=tip)
	if info["img"] and not info["prefer_text"]:
		p.add_html('<img alt="%s" class="dh-svg" src="%s"/>' % (info["name"], info["img"]))
	else:
		p.add_html(info["text"])
	p.end_span()

# OK
def parse_unclear(p, node):
	tip = "Unclear text"
	if node["cert"] == "low":
		tip = "Very unclear text"
	if node["reason"]:
		tip += " (%s)" % node["reason"].replace("_", " ")
	p.start_span(klass="dh-unclear", tip=tip)
	p.add_html("(")
	p.dispatch_children(node)
	if node["cert"] == "low":
		p.add_html("?")
	p.add_html(")")
	p.end_span()

# EGD "Editorial deletion (suppression)"
def parse_surplus(p, node):
	p.start_span(klass="dh-surplus", tip="Superfluous text erroneously added by the scribe")
	p.add_html("{")
	p.dispatch_children(node)
	p.add_html("}")
	p.end_span()

def parse_p(p, para):
	p.add_log("<para")
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
	"check": "mark",
	"grantha": {"klass": "dh-grantha", "tip": "Grantha text"},
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
			p.add_html("</%s>" % val)
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
	if x <= 0 or x > 3000:
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
	met = titlecase(lg["met"] or "unknown meter")
	p.add_log("<head", level=6)
	p.add_html("%s. %s" % (n, met))
	p.add_log(">head", level=6)
	p.add_log("<verse")
	p.dispatch_children(lg)
	p.add_log(">verse")

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
	typ = list["type"]
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
			p.dispatch_children(item)
			p.add_log(">item")
	p.add_log(">list", type=typ)

def parse_l(p, l):
	p.add_log("<line")
	p.dispatch_children(l)
	p.add_log(">line")

def extract_bib_ref(p, node):
	assert node.name == "bibl"
	ptr = node.first("ptr")
	if not ptr:
		return None, None
	target = ptr["target"]
	if not target.startswith("bib:"):
		p.complain(ptr)
		return None, None
	ref = target.removeprefix("bib:")
	loc = []
	for r in node.find("citedRange"):
		unit = r["unit"]
		if unit not in bibl_units:
			unit = "page"
		val = r.text().strip()
		if not val:
			continue
		loc.append((unit, val))
	return ref, loc

bibl_units = set(biblio.cited_range_units)

def parse_listBibl(p, node):
	recs = node.find("bibl")
	if not recs:
		return
	if all(len(rec) == 0 for rec in recs):
		return
	typ = node["type"]
	if typ:
		p.add_log("<head")
		p.add_text(titlecase(typ))
		p.add_log(">head")
	for rec in recs:
		ref, loc = extract_bib_ref(p, rec)
		if not ref:
			return #  TODO
		p.add_code("bib", ref, loc=loc, n=rec["n"])

def parse_bibl(p, node):
	rend = node["rend"]
	if rend not in ("omitname", "ibid", "default"):
		rend = "default"
	ref, loc = extract_bib_ref(p, node)
	if not ref:
		return # TODO
	p.add_code("ref", ref, rend=rend, loc=loc)

def parse_body(p, body):
	for elem in body.children():
		p.dispatch(elem)

def parse_title(p, title):
	p.dispatch_children(title)

def parse_q(p, q):
	p.add_html("“")
	p.dispatch_children(q)
	p.add_html("”")

def remove_duplicates(ls):
	ret = []
	for x in ls:
		if x not in ret:
			ret.append(x)
	return ret

"""
titleStmt =
  element titleStmt {
    title+,
    author?,
    editor*,
    element respStmt {
      (persName
       | element resp { text })+
    }*
  }
"""
def parse_titleStmt(p, stmt):
	titles = []
	for t in stmt.find("title"):
		text = t.text() # XXX not legit
		if not text:
			continue
		titles.append(text)
	p.push("title")
	for i, title in enumerate(titles):
		p.add_text(title)
		if i < len(titles) - 1:
			p.add_text(PARA_SEP)
	p.document.title = p.pop()
	p.push("author")
	author = [t.text() for t in stmt.find("author")] # XXX t.text() not legit
	assert len(author) <= 1, author
	author = author and author[0] or None
	p.add_text(author)
	p.document.author = p.pop()
	p.push("editors")
	editors = []
	for node in stmt.find("editor") + stmt.find("respStmt/persName"):
		ident = node["ref"]
		if ident == "part:jodo":
			continue
		if ident and ident.startswith("part:"):
			name = people.plain(ident.removeprefix("part:"))
		else:
			name = normalize_space(node.text(space="preserve"))
			if not name:
				continue
		editors.append(name)
	editors = remove_duplicates(editors)
	for editor in editors:
		p.start_item()
		p.add_text(editor)
	p.document.editors = p.pop()

def parse_sourceDesc(p, desc):
	summ = desc.find("msDesc/msContents/summary")
	assert len(summ) <= 1
	if not summ:
		return
	summ = summ[0]
	# remove paragraphs
	for para in summ.find(".//p"):
		para.unwrap()
	p.push("summary")
	p.dispatch_children(summ)
	p.document.summary = p.pop()

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

if __name__ == "__main__":
	t = tree.parse(sys.argv[1])
	p = Parser(t, HANDLERS)
	p.dispatch(p.tree.root)
