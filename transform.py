#!/usr/bin/env python3

"""
We apparently have 4 schemas for 4 types of texts:

* Inscriptions (INSSchema -> latest/Schema)
  Is it actually only for inscriptions, or also more generic stuff?
* Critical (CritEdSchema)
* Diplomatic (DiplEdSchema)
* BESTOW (in progress, so ignore for now)

Share code or not? Are schemas different enough to warrant distinct parsers?
"""

import sys, re
from bs4 import BeautifulSoup, NavigableString, Comment

class Parser:
	# True if we saw a space and are waiting to see a non-blank character
	# before emitting it
	had_space = False

# Like the eponymous function in xslt
def normalize_space(s):
	s = s.strip()
	return re.sub(r"\s+", " ", s)

def complain(elem):
	print("? %r" % elem)

def emit(p, t, data=None):
	if t == "text":
		if not data:
			return
		if p.had_space:
			if data.strip():
				print("space")
				p.had_space = False
		elif data[0].isspace():
			if data.lstrip():
				print("space")
				p.had_space = False
			else:
				p.had_space = True
		if re.match(r".*\S\s+$", data):
			p.had_space = True
		data = normalize_space(data)
		if data:
			print(t, repr(data))
	elif data is not None:
		print(t, repr(data))
	else:
		print(t)

def process_lemma(p, lemma):
	text = lemma.get_text()
	emit(p, "text", text)
	# Ignore the apparatus for now

def process_apparatus(p, app):
	for elem in app:
		if elem.name == "lem":
			lemma(p, elem)

def process_num(p, num):
	for elem in num:
		if isinstance(elem, Comment):
			pass
		elif isinstance(elem, NavigableString):
			emit(p, "text", elem)
		elif elem.name == "g":
			assert elem.string
			emit(p, "text", elem.string)
		else:
			assert 0, "%r" % elem

def process_supplied(p, supplied):
	for elem in supplied:
		if isinstance(elem, Comment):
			pass
		elif isinstance(elem, NavigableString):
			emit(p, "text", elem)
		elif elem.name == "num":
			process_num(p, elem)
		else:
			assert 0, "%r" % elem

def process_para(p, para):
	print("# para")
	for elem in para:
		if isinstance(elem, Comment):
			pass
		elif isinstance(elem, NavigableString):
			emit(p, "text", elem)
		elif elem.name == "lb":
			n = elem["n"].strip()
			emit(p, "line", n)
		elif elem.name == "num":
			process_num(p, elem)
		elif elem.name == "app":
			process_apparatus(p, elem)
		elif elem.name == "unclear":
			assert elem.string is not None
			emit(p, "text", elem.string)
		elif elem.name == "supplied":
			process_supplied(p, elem)
		else:
			complain(elem)
	emit(p, "para")

def process_div(p, div):
	t = div["type"]
	assert t in ("edition", "apparatus", "translation", "commentary", "bibliography")
	print("# div")
	for elem in div:
		if isinstance(elem, Comment):
			pass
		elif isinstance(elem, NavigableString):
			assert not elem.strip(), "%r" % elem
			emit(p, "text", " ")
		elif elem.name == "p":
			process_para(p, elem)
		else:
			complain(elem)
	emit(p, "div", t)

def process_body(p, soup):
	print("# body")
	body = soup.find("body")
	assert body
	for elem in body:
		if isinstance(elem, Comment):
			pass
		elif isinstance(elem, NavigableString):
			assert not elem.strip(), "%r" % elem
			emit(p, "text", " ")
		elif elem.name == "div":
			process_div(p, elem)
		elif elem.name == "p":
			process_para(p, elem)
		else:
			assert 0, "%r" % elem
	emit(p, "body")

soup = BeautifulSoup(sys.stdin, "xml")
p = Parser()
process_body(p, soup)
