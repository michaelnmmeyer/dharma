#!/usr/bin/env python3

import sys, re, io, copy
from dharma.tree import *

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
	emit(p, "<div>")
	type = div.attrs.get("type")
	if type in ("chapter", "title"):
		n = div.attrs.get("n")
		head = div.child("head")
		assert not head.previous_sibling
		if n:
			title = "%s %s: %s" % (type.title(), n, head.text()) # XXX not .text()!
		else:
			title = "%s: %s" % (type.title(), head.text()) # XXX not .text()!
		emit(p, "html", "<h%d>" % (p.div_level + p.heading_shift))
		emit(p, "title", title)
		emit(p, "html", "</h%d>" % (p.div_level + p.heading_shift))
	elif type in ("dyad", "liminal"):
		pass # TODO
	elif type == "metrical":
		assert div.parent.name == "div"
		# TODO
	elif not type:
		# Invocation or colophon
		ab = div.child("ab")
		assert not ab.previous_sibling
		type = ab["type"]
		assert type in ("invocation", "colophon")
		emit(p, ab["type"])
	else:
		assert 0, div
	emit(p, "</div>")
	p.div_level -= 1


def process_body(p, body):
	for div in body:
		if div.type == "string":
			assert not div.text().strip()
		else:
			assert div.type == "tag"
			assert div.name == "div"
			dispatch(p, div)

def process_TEI(p, node):
	dispatch(p, node.xpath("text/body")[0])

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
