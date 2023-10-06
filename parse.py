# to make sure we examine everything and to signal stuff we haven't taken into
# account, might want to add a "visited" flag to @. maybe id. for text nodes.

import os, sys, re, io, copy, html, unicodedata
from dharma import prosody, people, tree, gaiji

force_color = True
def term_color(code=None):
	if not os.isatty(1) and not force_color:
		return
	if not code:
		sys.stdout.write("\N{ESC}[0m")
		return
	code = code.lstrip("#")
	assert len(code) == 6
	R = int(code[0:2], 16)
	G = int(code[2:4], 16)
	B = int(code[4:6], 16)
	sys.stdout.write(f"\N{ESC}[38;2;{R};{G};{B}m")

def term_html(): term_color("#5f00ff")
def term_log(): term_color("#008700")
def term_text(): term_color("#aa007f")
def term_reset(): term_color()

def write_debug(t, data=None, **params):
	write = sys.stdout.write
	if t == "html":
		term_html()
	elif t.startswith("log:"):
		term_log()
	elif t == "text":
		term_text()
	write("%s" % t)
	if data:
		write(" %r" % data)
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

	# Whitespace state
	# drop: drop all spaces until we find some text
	# seen: saw space and waiting to see text before emitting ' '
	# none: waiting to see space
	space = "drop"

	def __init__(self, name=""):
		self.name = name
		self.text = ""
		self.code = []
		self.finished = False

	def __repr__(self):
		return "Block(%s):\n%s" % (self.name, "\n".join(repr(c) for c in self.code))

	def html(self):
		ret = []
		for t, data, _ in self.code:
			if t == "text":
				ret.append(data)
			elif t == "html":
				ret.append(data)
		return "".join(ret)

	def start_span(self):
		if self.text:
			self.add_text(PARA_SEP)

	def add_text(self, data):
		if not data:
			return
		if self.space == "drop":
			data = data.lstrip()
			if not data:
				return
			self.space = "none"
		elif self.space == "seen":
			if data.strip():
				self.text += " "
				self.space = "none"
		elif self.space == "none":
			if data[0].isspace():
				if data.lstrip():
					self.text += " "
					self.space = "none"
				else:
					self.space = "seen"
		else:
			assert 0
		if re.match(r".*\S\s+$", data):
			self.space = "seen"
		data = normalize_space(data)
		if not data:
			return
		self.text += data

	def flush(self):
		if not self.text:
			return
		rec = ("text", self.text, {})
		self.code.append(rec)
		write_debug(rec[0], rec[1], **rec[2])
		self.text = ""

	def add_html(self, data):
		return self.add_code("html", data)

	def add_code(self, t, data=None, **params):
		if self.space == "seen":
			self.text += " "
			self.space = "drop"
		if t == "html":
			self.flush()
		rec = (t, data, params)
		self.code.append(rec)
		write_debug(t, data, **params)

	def add_hyphen(self):
		self.space = "drop"
		# FIXME don't add one after pb, div, p, etc.
		self.add_html('<span class="dh-hyphen-break">-</span>')

	def finish(self):
		assert self.text == ""
		for i, (t, data, _) in enumerate(self.code):
			if t == "text":
				self.code[i] = ("text", data)
			elif t == "html":
				self.code[i] = ("html", data)
			else:
				self.code[i] = ("", "") # TODO
		self.finished = True

	def render(self):
		assert self.finished
		buf = []
		for t, data in self.code:
			if t == "text":
				text = html.escape(data)
				buf.append(text)
			elif t == "html":
				buf.append(data)
			else:
				pass
		return "".join(buf)

	def searchable_text(self):
		assert self.finished
		buf = []
		for t, data in self.code:
			if not t == "text":
				continue
			buf.append(data)
		return normalize("".join(buf))

class Section:

	heading = None
	contents = None

class Document:

	repository = ""
	ident = ""
	title = None
	author = None
	editors = None
	langs = None
	summary = None

	edition = None
	# we can have several translations e.g. DHARMA_INSPallava00002
	translation = None

	xml = ""

	def __init__(self):
		self.langs = []
		self.edition = []

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

	@property
	def top(self):
		return self.blocks[-1]

	def push(self, name):
		b = Block(name)
		self.blocks.append(b)
		return b

	def pop(self):
		b = self.blocks.pop()
		b.flush()
		b.finish()
		return b

	def add_text(self, text):
		return self.blocks[-1].add_text(text)

	def add_html(self, data):
		return self.blocks[-1].add_html(data)

	def add_code(self, t, data=None, **params):
		return self.blocks[-1].add_code(t, data, **params)

	def start_span(self):
		return self.blocks[-1].start_span()

	def dispatch(self, node):
		if node.type in ("comment", "instruction"):
			return
		if node.type == "string":
			return self.add_text(str(node))
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
		print("? %s" % msg)
		pass

# Like the eponymous function in xslt
def normalize_space(s):
	s = s.strip()
	return re.sub(r"\s+", " ", s)

def parse_lem(p, lemma):
	text = lemma.text() #XXX legit?
	p.add_text(text)
	# Ignore the apparatus for now

def parse_app(p, app):
	p.dispatch_children(app)

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
	p.add_html('<span class="dh-supplied" title="%s">' % html.escape(tip))
	if seps:
		p.add_html(seps[0])
	p.dispatch_children(supplied)
	if seps:
		p.add_html(seps[1])
	p.add_html('</span>')

def parse_foreign(p, foreign):
	p.add_html("<i>")
	p.dispatch_children(foreign)
	p.add_html("</i>")

def parse_milestone(p, milestone):
	assert "n" in milestone.attrs
	assert "unit" in milestone.attrs
	assert milestone["unit"] in ("block", "column", "face", "faces", "fragment", "item", "zone")
	# ignore for now
	return
	p.add_code(milestone["unit"], milestone["n"])

def parse_lb(p, elem):
	n = elem["n"]
	if not n:
		n = "?"
	brk = elem["break"]
	if brk not in ("yes", "no"):
		brk = "yes"
	# On alignment, EGD §7.5.2
	m = re.match(r"^text-align:\s*(right|center|left|justify)\s*$", elem["style"])
	if m:
		align = m.group(1)
	else:
		align = "left"
	if brk == "no":
		p.top.add_hyphen()
		klass = "dh-lb-cont"
	else:
		klass = "dh-lb"
	p.add_html('<span class="%s" data-num="%s" title="Line break"></span>' % (klass, html.escape(n)))

def parse_fw(p, fw):
	return # we deal with it within <pb>

places_arrows = {
	"": "",
	"left": "\N{LEFTWARDS ARROW}",
	"marginleft": "\N{LEFTWARDS ARROW}\N{LEFTWARDS ARROW}",
	"right": "\N{RIGHTWARDS ARROW}",
	"top-right": "\N{NORTH EAST ARROW}",
}
def parse_pb(p, elem):
	n = elem["n"]
	if not n:
		n = "?"
	brk = elem["break"]
	if brk not in ("yes", "no"):
		brk = "yes"
	if brk == "no":
		p.top.add_hyphen()
	fw = elem.next
	if fw and fw.name == "fw":
		place = places_arrows.get(fw["place"], "?")
	else:
		place = ""
	p.add_html('<span class="dh-pb" data-num="%s" title="Page break">' % html.escape(n))
	if place:
		p.add_html("%s " % html.escape(place))
		p.dispatch_children(fw)
	p.add_html('</span>')
	p.add_code("phys:page", n)

# OK
def parse_sic(p, sic):
	p.add_html('<span class="dh-sic" title="Incorrect text">')
	p.add_html("¿")
	p.dispatch_children(sic)
	p.add_html("?")
	p.add_html('</span>')

# OK
def parse_corr(p, corr):
	p.add_html('<span class="dh-corr" title="Corrected text">')
	p.add_html('⟨')
	p.dispatch_children(corr)
	p.add_html('⟩')
	p.add_html('</span>')

# OK
def parse_orig(p, orig):
	p.add_html('<span class="dh-orig" title="Non-standard text">')
	p.add_html("¡")
	p.dispatch_children(orig)
	p.add_html("!")
	p.add_html('</span>')

# OK
def parse_reg(p, reg):
	p.add_html('<span class="dh-reg" title="Standardised text">')
	p.add_html("⟨")
	p.dispatch_children(reg)
	p.add_html("⟩")
	p.add_html('</span>')

def parse_choice(p, node):
	children = node.children()
	if all(child.name == "unclear" for child in children):
		p.add_html('<span class="dh-choice-unclear" title="Unclear (several possible readings)">')
		p.add_html("(")
		sep = ""
		for child in children:
			p.add_html(sep)
			sep = "/"
			p.dispatch_children(child)
		p.add_html(")")
		p.add_html('</span>')
	else:
		# XXX deal with all possible cases
		# need to choose only one possibility for search (and for simplified display)
		# which one?
		p.dispatch_children(node)

def parse_space(p, space):
	p.add_html("_")
	assert not space.children()

def parse_abbr(p, node):
	p.add_html('<span class="dh-abbr" title="Abbreviated text">')
	p.dispatch_children(node)
	p.add_html('</span>')

def parse_ab(p, node):
	p.dispatch_children(node)

def parse_ex(p, node):
	p.add_html('<span class="dh-abbr-expansion" title="Abbreviation expansion">')
	p.dispatch_children(node)
	p.add_html('</span>')

def parse_expan(p, node):
	p.dispatch_children(node)

def parse_term(p, node):
	p.dispatch_children(node)

def parse_add(p, node):
	p.add_html('<span class="dh-add" title="Scribal addition">')
	p.dispatch_children(node)
	p.add_html('</span>')

def parse_del(p, node):
	p.add_html('<span class="dh-del" title="Scribal deletion">')
	p.dispatch_children(node)
	p.add_html('</span>')

def numberize(s, n):
	last_word = s.split()[-1].lower()
	if last_word not in ("character", "component", "line", "page", "editor"):
		print("cannot numberize term %r" % last_word, file=sys.stderr)
		return s
	if n == 1:
		return s
	return s + "s"

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
		# XXX repr here
		repl = "[%s]" % parent["met"]
	p.add_html('<span class="dh-gap" title="%s">%s</span>' % (html.escape(tip), html.escape(repl)))
	# TODO special cases in editorial, involve
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
	if st:
		t = "%s.%s" % (t, st)
	info = gaiji.get(t)
	tip = info["description"]
	tip_toks = tip.split(None, 1)
	if len(tip_toks) > 0:
		tip = tip_toks[0].title()
		if len(tip_toks) > 1:
			tip += " " + tip_toks[1]
	p.add_html('<span class="dh-symbol" title="%s (category: %s)">%s</span>' % \
		(html.escape(tip), html.escape(cat), html.escape(info["unicode"])))

# OK
def parse_unclear(p, node):
	tip = "Unclear text"
	if node["cert"] == "low":
		tip = "Very unclear text"
	if node["reason"]:
		tip += " (%s)" % node["reason"].replace("_", " ")
	p.add_html('<span class="dh-unclear" title="%s">' % html.escape(tip))
	p.add_html("(")
	p.dispatch_children(node)
	if node["cert"] == "low":
		p.add_html("?")
	p.add_html(")")
	p.add_html('</span>')

# EGD "Editorial deletion (suppression)"
def parse_surplus(p, node):
	p.add_html('<span class="dh-surplus" title="Superfluous text erroneously added by the scribe">')
	p.add_html("{")
	p.dispatch_children(node)
	p.add_html("}")
	p.add_html('</span>')

def parse_p(p, para):
	p.add_code("log:para<")
	p.add_html("<p>")
	p.dispatch_children(para)
	p.add_html("</p>")
	p.add_code("log:para>")

hi_table = {
	"italic": "i",
	"bold": "b",
	"superscript": "sup",
	"subscript": "sub",
	"large": "big",
	"check": "mark",
	"grantha": 'span class="dh-grantha" title="Grantha text"',
}
def parse_hi(p, hi):
	rend = hi["rend"]
	val = hi_table[rend]
	p.add_html("<%s>" % val)
	p.dispatch_children(hi)
	e = val.find(" ")
	if e < 0:
		e = len(val)
	p.add_html("</%s>" % val[:e])

def parse_lg(p, lg):
	pada = 0
	p.add_code("log:verse<")
	p.add_html('<div class="verse">')
	for elem in lg:
		if elem.type == "tag" and elem.name == "l":
			if pada % 2 == 0:
				p.add_html("<p>")
				p.dispatch_children(elem)
			else:
				p.add_text(" ")
				p.dispatch_children(elem)
				p.add_html("</p>")
			pada += 1
		else:
			p.dispatch(elem)
	p.add_html("</div>")
	p.add_code("log:verse>")

def parse_l(p, l):
	p.dispatch_children(l) # TODO

def parse_body(p, body):
	for elem in body.children():
		assert elem.type == "tag"
		p.dispatch(elem)

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
		text = t.text()
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
	author = [t.text() for t in stmt.find("author")]
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
		p.start_span()
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

def parse_TEI(p, node):
	p.dispatch(node.first("teiHeader"))
	p.dispatch(node.first("text/body"))

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
