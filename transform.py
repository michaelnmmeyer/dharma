#!/usr/bin/env python3

import sys, re, io
from dharma.tree import *

# XXX use a stack in the parser, or use recursion? if we want to recover
# (though this is another can of worms), we at least need to use some kind of
# wrapper for calling parsing functions. within the wrapper, we should do a
# try...catch

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

def complain(elem):
	print("? %r" % elem)

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
			lemma(p, elem)

def process_num(p, num):
	for elem in num:
		if elem.type == "comment":
			pass
		elif elem.type == "string":
			emit(p, "text", elem)
		elif elem.name == "g":
			assert elem.string
			emit(p, "text", elem.string)
		else:
			complain(elem)

def process_supplied(p, supplied):
	for elem in supplied:
		if elem.type == "comment":
			pass
		elif elem.type == "string":
			emit(p, "text", elem)
		elif elem.name == "num":
			process_num(p, elem)
		else:
			complain(elem)

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
	if len(node.attrs) != 1:
		fail()
	stype = node.get("type")
	if not stype:
		fail()
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
	emit(p, "symbol", f"{gtype}.{stype}")

def process_p(p, para):
	emit(p, "<para")
	for elem in para:
		if elem.type == "comment":
			pass
		elif elem.type == "string":
			emit(p, "text", elem)
		elif elem.name == "lb":
			process_lb(p, elem)
		elif elem.name == "pb":
			process_pb(p, elem)
		elif elem.name == "milestone":
			process_milestone(p, elem)
		elif elem.name == "num":
			process_num(p, elem)
		elif elem.name == "app":
			process_apparatus(p, elem)
		elif elem.name == "unclear":
			emit(p, "text", elem.text()) # XXX children?
		elif elem.name == "supplied":
			process_supplied(p, elem)
		elif elem.name == "g":
			process_g(p, elem)
		else:
			complain(elem)
	emit(p, ">para")

def process_div(p, div):
	t = div["type"]
	assert t in ("edition", "apparatus", "translation", "commentary", "bibliography")
	print("<div")
	for elem in div:
		if elem.type == "comment":
			pass
		elif elem.type == "string":
			assert not elem.strip(), "%r" % elem
			emit(p, "text", " ")
		elif elem.name == "p":
			process_p(p, elem)
		else:
			complain(elem)
	emit(p, ">div", t)

def process_body(p, root):
	print("<body")
	body = tree.find("body")
	assert body
	for elem in body:
		if elem.type == "comment":
			pass
		elif elem.type == "string":
			assert not elem.strip(), "%r" % elem
			emit(p, "text", " ")
		elif elem.name == "div":
			process_div(p, elem)
		elif elem.name == "p":
			process_p(p, elem)
		else:
			assert 0, "%r" % elem
	emit(p, ">body")

if __name__ == "__main__":
	tree = parse(sys.argv[1])
	p = Parser()
	p.tree = parse(sys.argv[1])
	process_body(p, p.tree.root)
