#!/usr/bin/env python3

# XXX apparently possible to annotate nodes in relaxng with java code; can we
# also do that with python? relaxng has a shorthand for documentation
# annotations: it interprets lines starting with '##' as documentation and
# outputs it in the generated XML. we can use that.
#
# or we can generate the code from an ODD file. or better yet, we can generate
# the ODD file from the code. in this case should annotate functions
# appropriately and have some predefined routines that can be mapped easily to
# ODD elements for the things that ODD can actually validate. look at what ODD
# can actually represent and adjust.
#
# in any case, should have both the schema and the processing code in the same
# file, so that we don't have to do checks several times.
#
# the only useful use of ODD/rng is help screens and autocompletion in oXygen
# and co. how does it work exactly? context-sensitive or not? yes it is, more
# complicated for us.

import sys, re, io, copy
from dharma.tree import *

HANDLERS = {} # we fill this below

def dispatch(p, node):
	if node.type == "comment" or node.type == "instruction":
		return
	if node.type == "string":
		emit(p, "text", node)
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
			print("%s %r" % (t, data))
	elif data is not None:
		write("%s %r" % (t, data))
		for k, v in sorted(params.items()):
			write(" %s %r" % (k, v))
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
	for attr, val in elem.attrs.items():
		if attr == "n":
			n = val
		elif attr == "break":
			brk = val
		else:
			assert 0, elem
	assert n
	assert brk in ("yes", "no")
	if brk == "yes":
		emit(p, "text", "\n")
	emit(p, "line", n)
	p.space = "drop"

def process_pb(p, elem):
	assert "n" in elem.attrs and len(elem.attrs) == 1
	n = elem["n"]
	emit(p, "page", n)
	p.space = "drop"

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
	t = div["type"]
	assert t in ("edition", "apparatus", "translation", "commentary", "bibliography")
	emit(p, "<div")
	for elem in div:
		dispatch(p, elem)
	emit(p, ">div", t)

def process_body(p, node):
	print("<body")
	for elem in node:
		dispatch(p, elem)
	emit(p, ">body")

def process_text(p, node):
	dispatch(p, node.child("body"))

def process_TEI(p, node):
	# ignore the header for now
	dispatch(p, node.child("text"))

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
