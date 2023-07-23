#!/usr/bin/env python3

import os, sys, re, io, copy
from dharma.tree import *
from dharma import prosody

HANDLERS = {} # we fill this below

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

class HTML:

	def __init__(self):
		self.buf = []

	def write(self, t, data=None, **params):
		write = sys.stdout.write
		if t == "text":
			assert not self.buf or self.buf[-1][0] != "text"
			write(data)
		elif t == "html":
			write(data)
		elif t == "log:doc>":
			write("\n")
		self.buf.append((t, data, params))

class Parser:
	# drop: drop all spaces until we find some text
	# seen: saw space and waiting to see text before emitting ' '
	# none: waiting to see space
	space = "drop"
	tree = None
	div_level = 0

	# For HTML output
	heading_shift = 1
	html_start = 0

	def __init__(self, tree, write=write_debug):
		self.tree = tree
		self.write = write
		self.text = ""

	def dispatch(self, node):
		if node.type == "comment" or node.type == "instruction":
			return
		if node.type == "string":
			self.emit("text", node, lang=node.parent["lang"])
			return
		assert node.type == "tag"
		f = HANDLERS.get(node.name)
		if not f:
			#p.complain("no handler for %r, ignoring it" % node)
			return
		try:
			f(p, node)
		except Error as e:
			p.complain(e)

	def dispatch_children(self, node):
		for child in node:
			self.dispatch(child)

	def complain(self, msg):
		print("? %s" % msg, file=sys.stderr)

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

	def emit(self, t, data=None, **params):
		if t == "text":
			self.add_text(data)
			return
		if t == "html" or t.startswith("log:"):
			if self.html_start < len(self.text):
				self.write("text", self.text[self.html_start:], start=self.html_start, end=len(self.text))
			self.html_start = len(self.text)
		p.space = "drop"
		self.write(t, data, **params)

def barf(msg):
	raise Exception(msg)

# Like the eponymous function in xslt
def normalize_space(s):
	s = s.strip()
	return re.sub(r"\s+", " ", s)

def process_lem(p, lemma):
	text = lemma.text() #XXX legit?
	p.emit("text", text)
	# Ignore the apparatus for now

def process_app(p, app):
	p.dispatch_children(app)

def process_num(p, num):
	p.dispatch_children(num)

def process_supplied(p, supplied):
	p.dispatch_children(supplied)

def process_milestone(p, milestone):
	assert "n" in milestone.attrs
	assert "unit" in milestone.attrs
	assert milestone["unit"] in ("block", "column", "face", "faces", "fragment", "item", "zone")
	# ignore for now
	return
	p.emit(milestone["unit"], milestone["n"])

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
		p.emit("text", "\n")
	p.emit("phys:line", n, {"align": align})
	p.space = "drop"

def process_pb(p, elem):
	n = elem["n"]
	# ignore for now, incomplete
	return
	p.emit("phys:page", n)
	p.space = "drop"

def process_choice(p, node):
	p.dispatch_children(node)

def process_abbr(p, node):
	p.dispatch_children(node)

def process_term(p, node):
	p.dispatch_children(node)

def process_g(p, node):
	def fail():
		 barf("invalid node (see STS)")
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
		fail()
	if len(node.attrs) != 1:
		fail()
	stype = node.get("type")
	if not stype:
		fail()
	p.emit("symbol", f"{gtype}.{stype}")

def process_unclear(p, node):
	p.emit("text", node.text()) # XXX children?

def process_p(p, para):
	p.emit("log:para<")
	p.emit("html", "<p>")
	p.dispatch_children(para)
	p.emit("html", "</p>")
	p.emit("log:para>")

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
	p.emit("html", "<%s>" % val)
	p.dispatch_children(hi)
	e = max(val.find(" "), len(val))
	p.emit("html", "</%s>" % val[:e])

def process_div_head(p, head):
	def inner(root):
		for elem in root:
			if elem.type == "tag":
				if elem.name == "foreign":
					p.emit("html", "<i>")
					inner(elem)
					p.emit("html", "</i>")
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
	p.emit("log:verse<")
	p.emit("html", '<div class="verse">')
	for elem in lg:
		if elem.type == "tag" and elem.name == "l":
			if pada % 2 == 0:
				p.emit("html", "<p>")
				p.dispatch_children(elem)
			else:
				p.emit("text", " ")
				p.dispatch_children(elem)
				p.emit("html", "</p>")
			pada += 1
		else:
			p.dispatch(elem)
	p.emit("html", "</div>")
	p.emit("log:verse>")

def process_div_dyad(p, div):
	for elem in div:
		if elem.type == "tag" and elem.name == "quote":
			assert elem.attrs.get("type") == "base-text"
			p.emit("html", '<div class="base-text">')
			p.dispatch_children(elem)
			p.emit("html", "</div>")
		else:
			p.dispatch(elem)

def process_div_section(p, div):
	ignore = None
	type = div.attrs.get("type", "")
	if type in ("chapter", "canto"):
		p.emit("log:head<", level=p.div_level)
		p.emit("html", "<h%d>" % (p.div_level + p.heading_shift))
		p.emit("text", type.title())
		n = div.attrs.get("n")
		if n:
			p.emit("text", " %s" % n)
		head = div.first_child("head")
		if head:
			p.emit("text", ": ")
			process_div_head(p, head)
			ignore = head
		p.emit("html", "</h%d>" % (p.div_level + p.heading_shift))
		p.emit("log:head>")
	elif not type:
		ab = div.first_child("ab")
		if ab:
			# Invocation or colophon?
			type = ab["type"]
			assert type in ("invocation", "colophon")
			p.emit("log:%s<" % ab["type"])
			process_div_ab(p, ab)
			p.emit("log:%s>" % ab["type"])
			ignore = ab
	else:
		assert 0, div
	# Render the meter
	if type != "chapter":
		rend = div.attrs.get("rend", "")
		assert rend == "met" or not rend
		if rend:
			met = div["met"]
			p.emit("html", "<h%d>" % (p.div_level + p.heading_shift + 1))
			if met.isalpha():
				pros = prosody.items.get(met)
				assert pros, "meter %r absent from prosodic patterns file" % met
				p.emit("blank", "%s: %s" % (met.title(), pros))
			p.emit("html", "</h%d>" % (p.div_level + p.heading_shift + 1))
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
	p.emit("html", "<div>")
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
	p.emit("html", "</div>")

# The full table is at:
# https://iso639-3.sil.org/sites/iso639-3/files/downloads/iso-639-3.tab
# For scripts see:
# https://www.unicode.org/iso15924/iso15924.txt

LANGS = """
ara
ban
cja
cjm
deu
eng
fra
ind
jav
jpn
kan
kaw
khm
mya
ndl
obr
ocm
okz
omx
omy
ori
osn
pli
pyx
san
sas
tam
tel
tgl
und
vie
xhm
zlm
""".strip().split()

def process_body(p, body):
	for div in body.children():
		assert div.type == "tag"
		assert div.name == "div"
		p.dispatch(div)

def process_TEI(p, node):
	p.dispatch(node.child("text").child("body"))

for name, obj in copy.copy(globals()).items():
	if not name.startswith("process_"):
		continue
	name = name.removeprefix("process_")
	HANDLERS[name] = obj

head = """
<!doctype html>
<html lang="en">
<head>
	<meta charset="utf-8">
	<title>foo</title>
	<link rel="preconnect" href="https://fonts.googleapis.com">
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
	<link href="https://fonts.googleapis.com/css2?family=Noto+Sans:ital@0;1&display=swap" rel="stylesheet">
	<link rel="stylesheet" href="style.css">
</head>
</body>
"""
tail = """
</body>
</html>
"""

if __name__ == "__main__":
	p = Parser(None)
	tree = parse(sys.argv[1])
	#p = Parser(tree, HTML().write)
	p = Parser(tree)
	p.emit("log:doc<")
	print(head)
	p.emit("html", '<div class="edition">')
	p.dispatch(p.tree.root)
	p.emit("html", "</div>")
	print(tail)
	p.emit("log:doc>")
