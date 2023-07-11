#!/usr/bin/env python3

import sys, re, io, copy
from dharma.tree import *
from dharma import prosody

HANDLERS = {} # we fill this below

def dispatch(p, node):
	if node.type == "comment" or node.type == "instruction":
		return
	if node.type == "string":
		emit(p, "text", node, {"lang": node.parent["lang"]})
		return
	assert node.type == "tag"
	f = HANDLERS.get(node.name)
	if not f:
		complain(p, "no handler for %r, ignoring it" % node)
		return
	try:
		f(p, node)
	except Error as e:
		complain(p, e)

class Parser:
	# drop: drop all spaces until we find some text
	# seen: saw space and waiting to see text before emitting ' '
	# none: waiting to see space
	space = "drop"
	tree = None
	div_level = 0

	# For HTML output
	heading_shift = 1

def barf(msg):
	raise Exception(msg)

# Like the eponymous function in xslt
def normalize_space(s):
	s = s.strip()
	return re.sub(r"\s+", " ", s)

def complain(p, msg):
	print("? %s" % msg)

def emit(p, t, data=None, params={}):
	write = sys.stdout.write
	if t == "text":
		if not data:
			return
		if p.space == "drop":
			data = data.lstrip()
		elif p.space == "seen":
			if data.strip():
				print("space")
				p.space = "none"
		elif p.space == "none":
			if data[0].isspace():
				if data.lstrip():
					print("space")
					p.space = "none"
				else:
					p.space = "seen"
		else:
			assert 0
		if re.match(r".*\S\s+$", data):
			p.space = "seen"
		data = normalize_space(data)
		if data:
			write("%s %r" % (t, data))
			for k, v in sorted(params.items()):
				write(" :%s %r" % (k, v))
			write("\n")
	elif data is not None:
		write("%s %r" % (t, data))
		for k, v in sorted(params.items()):
			write(" :%s %r" % (k, v))
		write("\n")
	else:
		print(t)

def process_lemma(p, lemma):
	text = lemma.text()
	emit(p, "text", text)
	# Ignore the apparatus for now

def process_apparatus(p, app):
	for elem in app:
		if elem.name == "lem":
			process_lemma(p, elem)

def process_num(p, num):
	for elem in num:
		dispatch(p, elem)

def process_supplied(p, supplied):
	for elem in supplied:
		dispatch(p, elem)

def process_milestone(p, milestone):
	assert "n" in milestone.attrs
	assert "unit" in milestone.attrs
	assert milestone["unit"] in ("block", "column", "face", "faces", "fragment", "item", "zone")
	# ignore the rest for now
	emit(p, milestone["unit"], milestone["n"])

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
	if brk == "yes":
		emit(p, "text", "\n")
	emit(p, "<phys:line", n, {"align": align})
	p.space = "drop"

def process_pb(p, elem):
	n = elem["n"]
	emit(p, "page", n)
	p.space = "drop"
	# XXX incomplete

def process_choice(p, node):
	for elem in node:
		if elem.type == "comment":
			continue
		if not elem.type == "tag":
			raise Error(node, "expected an element")
		dispatch(p, elem)

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
	emit(p, "symbol", f"{gtype}.{stype}")

def process_unclear(p, node):
	emit(p, "text", node.text()) # XXX children?

def process_p(p, para):
	emit(p, "<para")
	for elem in para:
		dispatch(p, elem)
	emit(p, ">para")

def process_div(p, div):
	p.div_level += 1
	emit(p, "html", "<div>")
	type = div.attrs.get("type", "")
	if type in ("chapter", "canto"):
		title = type.title()
		n = div.attrs.get("n")
		if n:
			title += " %s" % n
		head = div.first_child("head")
		if head:
			title += ": %s" % head.text() # XXX not .text()!
		emit(p, "html", "<h%d>" % (p.div_level + p.heading_shift))
		emit(p, "title", title)
		emit(p, "html", "</h%d>" % (p.div_level + p.heading_shift))
	elif type == "dyad":
		pass
		# TODO
	elif type == "metrical":
		# Group of verses that share the same meter. Don't exploit this for now.
		assert p.div_level > 1, '<div type="metrical"> can only be used as a child of another <div>'
	elif type == "interpolation":
		# Ignore for now.
		pass
	elif not type:
		ab = div.first_child("ab")
		if ab:
			# Invocation or colophon?
			type = ab["type"]
			assert type in ("invocation", "colophon")
			emit(p, ab["type"])
	else:
		assert 0, div
	# Render the meter
	if type != "chapter":
		rend = div.attrs.get("rend", "")
		assert rend == "met" or not rend
		if rend:
			met = div["met"]
			emit(p, "html", "<h%d>" % (p.div_level + p.heading_shift + 1))
			if met.isalpha():
				pros = prosody.items[met]
				emit(p, "blank", "%s: %s" % (met.title(), pros))
			emit(p, "html", "</h%d>" % (p.div_level + p.heading_shift + 1))
		else:
			# If we have @met, could use it as a search attribute. Is it often used?
			pass
	else:
		assert not div.attrs.get("rend")
		assert not div.attrs.get("met")
	emit(p, "html", "</div>")
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

"""
texts/DHARMA_CritEdSvayambhu.xml
texts/DHARMA_INSCIK00139.xml
"""

def process_body(p, body):
	for div in body.children():
		assert div.type == "tag"
		assert div.name == "div"
		dispatch(p, div)

def process_TEI(p, node):
	dispatch(p, node.child("text").child("body"))

for name, obj in copy.copy(globals()).items():
	if not name.startswith("process_"):
		continue
	name = name.removeprefix("process_")
	HANDLERS[name] = obj

if __name__ == "__main__":
	tree = parse(sys.argv[1])
	p = Parser()
	p.tree = parse(sys.argv[1])
	dispatch(p, p.tree.root)
