#!/usr/bin/env python3

import os, io, unicodedata
from bs4 import BeautifulSoup, Tag
from dharma.transform import normalize_space

this_dir = os.path.dirname(os.path.abspath(__file__))
path = "repos/project-documentation/DHARMA_idListMembers_v01.xml"
path = os.path.join(this_dir, path)

with open(path) as f:
	text = unicodedata.normalize("NFC", f.read())
	soup = BeautifulSoup(io.StringIO(text), "xml")

def count_children_tags(iter):
	n = 0
	for x in iter:
		if isinstance(x, Tag):
			n += 1
	return n

persons = {}

for person in soup.find_all("person"):
	ident = person["xml:id"].strip()
	rec = person.persName
	name = rec.find("name")
	assert ident not in persons
	if name:
		assert count_children_tags(rec.children) == 1, rec
		name = normalize_space(name.get_text())
		persons[ident] = [name]
	else:
		assert count_children_tags(rec.children) == 2, rec
		first = normalize_space(rec.forename.get_text())
		last = normalize_space(rec.surname.get_text())
		persons[ident] = [first, last]

def plain(ident):
	return " ".join(persons[ident])

def html(ident, root_tag):
	rec = persons[ident]
	soup = BeautifulSoup(f"<{root_tag}></{root_tag}>", "xml")
	root = soup.find(root_tag)
	root["ref"] = "part:%s" % ident
	if len(rec) == 1:
		root.name = rec[0]
	else:
		first = soup.new_tag("forename")
		first.string = rec[0]
		last = soup.new_tag("surname")
		last.string = rec[1]
		root.append(first)
		root.append(last)
	return root

if __name__ == "__main__":
	for ident, name in sorted(persons.items()):
		print(ident, " ".join(name), sep="\t")
