import os
from glob import glob
from dharma import tree

def all_texts():
	for file in glob("texts/DHARMA_INS*.xml"):
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
for file in all_texts():
	xml = tree.parse(file)
	root = xml.first("TEI")
	if not root:
		continue
	accumulate(root, tbl)

for k, vs in sorted(tbl.items()):
	print(k, vs)
