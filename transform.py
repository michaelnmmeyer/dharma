#!/usr/bin/env python3

import sys, re
from bs4 import BeautifulSoup, NavigableString

class Parser:
	had_space = False

# Like the eponymous function in xslt
def normalize_space(s):
	s = s.strip()
	return re.sub(r"\s+", " ", s)

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

def parse_lemma(p, lemma):
	text = lemma.get_text()
	emit(p, "text", text)
	# Ignore the apparatus for now

def parse_apparatus(p, app):
	for elem in app:
		if elem.name == "lem":
			parse_lemma(p, elem)

def parse_body(p, soup):
	body = soup.find("body")
	for para in body.find_all("p"): # XXX not only p!
		for elem in para:
			if isinstance(elem, NavigableString):
				emit(p, "text", elem)
			elif elem.name == "app":
				parse_apparatus(p, elem)

soup = BeautifulSoup(sys.stdin, "xml")
p = Parser()
parse_body(p, soup)
