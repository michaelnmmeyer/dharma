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
	had_space = False

# Like the eponymous function in xslt
def normalize_space(s):
	s = s.strip()
	return re.sub(r"\s+", " ", s)

def complain(elem):
	print("? %r" % elem, file=sys.stderr)

def emit(p, t, data=None):
	if t == "text":
		if p.had_space or re.match(r"\s+\S", data):
			print("space")
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

def process_para(p, para):
	for elem in para:
		if isinstance(elem, NavigableString):
			emit(p, "text", elem)
		elif elem.name == "app":
			process_apparatus(p, elem)
		else:
			complain(elem)

def process_div(p, div):
	emit(p, "div", div.get("type", "null"))
	for elem in div:
		if isinstance(elem, Comment):
			pass
		elif isinstance(elem, NavigableString):
			print(elem)
		elif elem.name == "p":
			process_para(p, elem)
		else:
			complain(elem)

def process_body(p, soup):
	body = soup.find("body")
	for elem in body:
		if isinstance(elem, Comment):
			pass
		elif isinstance(elem, NavigableString):
			assert not elem.strip(), "%r" % elem
		elif elem.name == "div":
			process_div(p, elem)
		elif elem.name == "p":
			process_para(p, elem)
		else:
			assert 0, "%r" % elem
			
soup = BeautifulSoup(sys.stdin, "xml")
p = Parser()
process_body(p, soup)
