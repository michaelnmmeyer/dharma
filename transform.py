#!/usr/bin/env python3

import os, sys, re, io, copy
from dharma.tree import *
from dharma import prosody

HANDLERS = {} # we fill this below

if os.isatty(1):
	def term_blue():
		sys.stdout.write("\N{ESC}[34m")
	
	def term_reset():
		sys.stdout.write("\N{ESC}[0m")
else:
	def term_blue(): pass
	def term_reset(): pass

class Parser:
	# drop: drop all spaces until we find some text
	# seen: saw space and waiting to see text before emitting ' '
	# none: waiting to see space
	space = "drop"
	tree = None
	div_level = 0
	
	raw_indent = 0

	# For HTML output
	heading_shift = 1
	
	def __init__(self, tree):
		self.tree = tree
		self.buf = []

	def dispatch(self, node):
		if node.type == "comment" or node.type == "instruction":
			return
		if node.type == "string":
			self.emit("text", node, lang=node.parent["lang"])
			return
		assert node.type == "tag"
		f = HANDLERS.get(node.name)
		if not f:
			p.complain("no handler for %r, ignoring it" % node)
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
	
	def indent(self):
		self.raw_indent += 1
	
	def dedent(self):
		self.raw_indent -= 1
	
	def vspace(self):
		self.emit("raw", "\n")
	
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
				self.buf.append(" ")
				self.space = "none"
		elif self.space == "none":
			if data[0].isspace():
				if data.lstrip():
					self.buf.append(" ")
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
		self.buf.append(data)
	
	def write2(self, t, data=None, **params):
		write = sys.stdout.write
		if t == "html":
			term_blue()
		write("%s" % t)
		if data:
			write(" %r" % data)
		if params:
			for k, v in sorted(params.items()):
				write(" :%s %r" % (k, v))
		if t == "html":
			term_reset()
		write("\n")
	
	def write(self, t, data=None, **params):
		if t == "text":
			print(self.raw_indent * "\t" + data)
		elif t == "raw":
			sys.stdout.write(data)
		else:
			pass#print(t, data, **params)

	def flush_text(self):
		if not self.buf:
			return
		self.write("text", "".join(self.buf))
		self.buf.clear()
	
	def emit(self, t, data=None, **params):
		if t == "text":
			self.add_text(data)
			return
		self.flush_text()
		p.space = "drop"
		if data is not None:
			self.write(t, data, **params)
		else:
			self.write(t)

def barf(msg):
	raise Exception(msg)

# Like the eponymous function in xslt
def normalize_space(s):
	s = s.strip()
	return re.sub(r"\s+", " ", s)

def process_lem(p, lemma):
	text = lemma.text()
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
	p.vspace()
	p.emit("log:para>")

def process_div_head(p, head):
	def inner(root):
		for elem in root:
			if elem.type == "tag":
				if elem.name == "foreign":
					p.emit("html", "<i>")
					inner(elem)
					p.emit("html", "</i>")
				elif elem.name == "hi":
					# TODO
					inner(elem)
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
	p.emit("html", '<div type="verse">')
	for elem in lg:
		if elem.type == "tag" and elem.name == "l":
			if pada % 2 == 0:
				p.emit("html", "<p>")
				p.dispatch_children(elem)
			else:
				p.emit("text", " ")
				p.dispatch_children(elem)
				p.emit("html", "</p>")
				p.emit("plain", "\n")
			pada += 1
		else:
			p.dispatch(elem)
	p.emit("html", "</div>")
	p.emit("log:verse>")

def process_div_dyad(p, div):
	for elem in div:
		if elem.type == "tag" and elem.name == "quote":
			assert elem.attrs.get("type") == "base-text"
			p.indent()
			p.emit("html", "<blockquote>")
			p.dispatch_children(elem)
			p.emit("html", "</blockquote>")
			p.dedent()
			p.vspace()
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
		p.vspace()
		p.emit("log:head>")
	elif not type:
		ab = div.first_child("ab")
		if ab:
			# Invocation or colophon?
			type = ab["type"]
			assert type in ("invocation", "colophon")
			p.emit("log:%s" % ab["type"])
			process_div_ab(p, ab)
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
	p.div_level += 1
	p.emit("html", "<div>")
	type = div.attrs.get("type", "")
	if type in ("chapter", "canto", ""):
		process_div_section(p, div)
		p.vspace()
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
	p.div_level -= 1

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
""".strip().split() + """
kan-Latn
kaw-Latn
khm-Latn
ocm-Latn
okz-Latn
omy-Latn
ori-Latn
osn-Latn
pli-Latn
pli-Thai
pra-Latn
san-Latn
san-Thai
tam-Latn
tam-Taml
tel-Latn
tha-Thai
xhm-Latn
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

if __name__ == "__main__":
	p = Parser(None)
	tree = parse(sys.argv[1])
	p = Parser(tree)
	p.dispatch(p.tree.root)
	p.emit("end")
