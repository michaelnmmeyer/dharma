#!/usr/bin/env python3

import os
from glob import glob
from dharma import tree

def all_valid_texts():
	for file in glob("texts/*.xml"):
		# Ignore invalid XML files
		base, _ = os.path.splitext(file)
		if os.path.exists(base + ".err"):
			continue
		yield file

def accumulate(elem, tbl):
	tbl.setdefault(elem.name, {"attrs": set(), "children": set()})
	for attr in elem.attrs:
		tbl[elem.name]["attrs"].add(attr)
	for child in elem:
		if child.type == "string":
			if child.strip():
				tbl[elem.name]["children"].add("*string*")
			continue
		if child.type == "tag":
			tbl[elem.name]["children"].add(child.name)
			accumulate(child, tbl)

tbl = {}
for file in all_valid_texts():
	xml = tree.parse(file)
	root = xml.first("TEI")
	if not root:
		# XXX apparently files that don't have TEI as root are still
		# deemed valid!
		continue
	accumulate(root, tbl)

for k, vs in sorted(tbl.items()):
	print(k, vs)
