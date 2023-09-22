#!/usr/bin/env python3

import os, sys, re, io, copy, html, unicodedata
from dharma.tree import *
from dharma import prosody, persons

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
def term_reset(): term_color()

def write_debug(t, data=None, **params):
	write = sys.stdout.write
	if t == "html":
		term_html()
	elif t.startswith("log:"):
		term_log()
	write("%s" % t)
	if data:
		write(" %r" % data)
	if params:
		for k, v in sorted(params.items()):
			write(" :%s %r" % (k, v))
	if t == "html" or t.startswith("log:"):
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

	def add_code(self, t, data=None, **params):
		if self.space == "seen":
			self.text += " "
			self.space = "drop"
		if t == "html":
			self.flush()
		rec = (t, data, params)
		self.code.append(rec)
		write_debug(t, data, **params)

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

class Document:

	repository = ""
	ident = ""
	title = None
	author = None
	editors = None
	langs = None
	summary = None

	def __init__(self):
		self.langs = []

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
		except Error as e:
			self.complain(e)

	def dispatch_children(self, node):
		for child in node:
			self.dispatch(child)

	def complain(self, msg):
		print("? %s" % msg, file=sys.stderr)
		pass

# Like the eponymous function in xslt
def normalize_space(s):
	s = s.strip()
	return re.sub(r"\s+", " ", s)

def process_lem(p, lemma):
	text = lemma.text() #XXX legit?
	p.add_text(text)
	# Ignore the apparatus for now

def process_app(p, app):
	p.dispatch_children(app)

def process_num(p, num):
	p.dispatch_children(num)

supplied_format = {
	"subaudible": "[]",
	"omitted": "⟨⟩",
	"explanation": "()",
	"supplied": "",
	"lost": "[]",
	"undefined": "[]",
}
def process_supplied(p, supplied):
	reason = supplied["reason"]
	format = supplied_format.get(reason)
	if format:
		p.add_code("html", format[0])
		p.dispatch_children(supplied)
		p.add_code("html", format[1])
	else:
		p.dispatch_children(supplied)

def process_foreign(p, foreign):
	p.add_code("html", "<i>")
	p.dispatch_children(foreign)
	p.add_code("html", "</i>")

def process_milestone(p, milestone):
	assert "n" in milestone.attrs
	assert "unit" in milestone.attrs
	assert milestone["unit"] in ("block", "column", "face", "faces", "fragment", "item", "zone")
	# ignore for now
	return
	p.add_code(milestone["unit"], milestone["n"])

def process_lb(p, elem):
	brk = "yes"
	n = None
	# On alignement, EGD §7.5.2
	align = "left" # assumption
	if not "n" in elem.attrs:
		raise Error(node, "attribute @n is required")
	for attr, val in elem.attrs.items():
		if attr == "n":
			n = val
		elif attr == "break":
			if brk not in ("yes", "no"):
				raise Error(node, "bad value for @break")
			brk = val
		elif attr == "style":
			m = re.match(r"^text-align:\s*(right|center|left|justify)\s*$", val)
			if not m:
				raise Error(node, "bad value for @style")
			align = m.group(1)
		else:
			assert 0, elem
	# ignore for now
	return
	if brk == "yes":
		p.add_text("\n")
	p.add_code("phys:line", n, {"align": align})
	p.space = "drop"

def process_pb(p, elem):
	n = elem["n"]
	# ignore for now, incomplete
	return
	p.add_code("phys:page", n)
	p.space = "drop"

def process_choice(p, node):
	p.dispatch_children(node)

def process_abbr(p, node):
	p.dispatch_children(node)

def process_term(p, node):
	p.dispatch_children(node)

def process_g(p, node):
	# <g type="...">.</g> for punctuation marks
	# <g type="...">§</g> for space fillers
	# <g type="..."></g> in the other cases viz. for symbols
	# 	whose functions is unclear
	text = node.text()
	if text == ".":
		gtype = "punctuation"
	elif text == "§":
		gtype = "space-filler"
	elif text == "":
		gtype = "unclear"
	else:
		assert 0, node
	if len(node.attrs) != 1:
		assert 0, node
	stype = node.get("type")
	assert stype, node
	p.add_code("symbol", f"{gtype}.{stype}")

def process_unclear(p, node):
	p.add_text(node.text()) # XXX children?

def process_p(p, para):
	p.add_code("log:para<")
	p.add_code("html", "<p>")
	p.dispatch_children(para)
	p.add_code("html", "</p>")
	p.add_code("log:para>")

hi_table = {
	"italic": "i",
	"bold": "b",
	"superscript": "sup",
	"subscript": "sub",
	"large": "big",
	"check": "mark",
	"grantha": 'span class="grantha"',
}
def process_hi(p, hi):
	rend = hi["rend"]
	val = hi_table[rend]
	p.add_code("html", "<%s>" % val)
	p.dispatch_children(hi)
	e = val.find(" ")
	if e < 0:
		e = len(val)
	p.add_code("html", "</%s>" % val[:e])

def process_div_head(p, head):
	def inner(root):
		for elem in root:
			if elem.type == "tag":
				if elem.name == "foreign":
					p.add_code("html", "<i>")
					inner(elem)
					p.add_code("html", "</i>")
				elif elem.name == "hi":
					p.dispatch(elem)
				else:
					assert 0
			else:
				p.dispatch(elem)
	inner(head)

def process_div_ab(p, ab):
	p.dispatch_children(ab)

def process_lg(p, lg):
	pada = 0
	p.add_code("log:verse<")
	p.add_code("html", '<div class="verse">')
	for elem in lg:
		if elem.type == "tag" and elem.name == "l":
			if pada % 2 == 0:
				p.add_code("html", "<p>")
				p.dispatch_children(elem)
			else:
				p.add_text(" ")
				p.dispatch_children(elem)
				p.add_code("html", "</p>")
			pada += 1
		else:
			p.dispatch(elem)
	p.add_code("html", "</div>")
	p.add_code("log:verse>")

def process_div_dyad(p, div):
	for elem in div:
		if elem.type == "tag" and elem.name == "quote":
			assert elem.attrs.get("type") == "base-text"
			p.add_code("html", '<div class="base-text">')
			p.dispatch_children(elem)
			p.add_code("html", "</div>")
		else:
			p.dispatch(elem)

def process_div_section(p, div):
	ignore = None
	type = div.attrs.get("type", "")
	if type in ("chapter", "canto"):
		p.add_code("log:head<", level=p.div_level)
		p.add_code("html", "<h%d>" % (p.div_level + p.heading_shift))
		p.add_text(type.title())
		n = div.attrs.get("n")
		if n:
			p.add_text(" %s" % n)
		head = div.find("head")
		if head:
			head = head[0]
			p.add_text(": ")
			process_div_head(p, head)
			ignore = head
		p.add_code("html", "</h%d>" % (p.div_level + p.heading_shift))
		p.add_code("log:head>")
	elif not type:
		ab = div.find("ab")
		if ab:
			ab = ab[0]
			# Invocation or colophon?
			type = ab["type"]
			assert type in ("invocation", "colophon")
			p.add_code("log:%s<" % ab["type"])
			process_div_ab(p, ab)
			p.add_code("log:%s>" % ab["type"])
			ignore = ab
	else:
		assert 0, div
	# Render the meter
	if type != "chapter":
		rend = div.attrs.get("rend", "")
		assert rend == "met" or not rend
		if rend:
			met = div["met"]
			p.add_code("html", "<h%d>" % (p.div_level + p.heading_shift + 1))
			if met.isalpha():
				pros = prosody.items.get(met)
				assert pros, "meter %r absent from prosodic patterns file" % met
				p.add_code("blank", "%s: %s" % (met.title(), pros))
			p.add_code("html", "</h%d>" % (p.div_level + p.heading_shift + 1))
		else:
			# If we have @met, could use it as a search attribute. Is it often used?
			pass
	else:
		assert not div.attrs.get("rend")
		assert not div.attrs.get("met")
	#  Display the contents
	for elem in div:
		if elem == ignore:
			continue
		p.dispatch(elem)

def process_div(p, div):
	p.add_code("html", "<div>")
	type = div.attrs.get("type", "")
	if type in ("chapter", "canto", ""):
		p.div_level += 1
		process_div_section(p, div)
		p.div_level -= 1
	elif type == "dyad":
		process_div_dyad(p, div)
	elif type == "metrical":
		# Group of verses that share the same meter. Don't exploit this for now.
		assert p.div_level > 1, '<div type="metrical"> can only be used as a child of another <div>'
		p.dispatch_children(div)
	elif type == "interpolation":
		# Ignore for now.
		p.dispatch_children(div)
	else:
		assert 0, div
	p.add_code("html", "</div>")

# The full table is at:
# https://iso639-3.sil.org/sites/iso639-3/files/downloads/iso-639-3.tab
# For scripts see:
# https://www.unicode.org/iso15924/iso15924.txt

def process_body(p, body):
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
def process_titleStmt(p, stmt):
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
		ident = node.get("ref")
		if ident == "part:jodo":
			continue
		if ident and ident.startswith("part:"):
			name = persons.plain(ident.removeprefix("part:"))
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

def process_sourceDesc(p, desc):
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

def process_fileDesc(p, node):
	p.dispatch_children(node)

def process_teiHeader(p, node):
	p.dispatch_children(node)

def process_TEI(p, node):
	p.dispatch(node.find("teiHeader")[0])
	#p.dispatch(node.find("text/body")[0])

def make_handlers_map():
	ret = {}
	for name, obj in copy.copy(globals()).items():
		if not name.startswith("process_"):
			continue
		name = name.removeprefix("process_")
		ret[name] = obj
	return ret

if __name__ == "__main__":
	tree = parse(sys.argv[1])
	p = Parser(tree, make_handlers_map())
	p.dispatch(p.tree.root)

	print("---")
	print(p.document.title)
	print(p.document.editors)
	print(p.document.summary)
	print("---")
	p.document.summary.render(); print()
	print("---")
	print(p.document.summary.searchable_text())
