# For parsing inscriptions.

import copy, sys
from dharma import tree, parse

def parse_div(p, div):
	type = div["type"]
	assert type == "textpart", div
	n = div["n"]
	assert n, div
	section = parse.Section()
	children = div.children()
	if children and children[0].name == "head":
		p.push("heading")
		p.dispatch_children(children[0])
		section.heading = p.pop()
	p.push("contents")
	for child in children[1:]:
		p.dispatch_children(child)
	section.contents = p.pop()
	p.document.edition.append(section)

def parse_body(p, body):
	for div in body.children():
		assert div.type == "tag" and div.name == "div"
		type = div["type"]
		if type == "edition":
			p.push("edition")
			p.dispatch_children(div)
			p.document.edition = p.pop()
		else:
			print("? %s" % div)

def update_handlers_map(m):
	for name, obj in copy.copy(globals()).items():
		if not name.startswith("parse_"):
			continue
		name = name.removeprefix("parse_")
		m[name] = obj

HANDLERS = parse.HANDLERS.copy()
update_handlers_map(HANDLERS)

if __name__ == "__main__":
	t = tree.parse(sys.argv[1])
	t.first("//teiHeader/encodingDesc").delete()
	t.first("//teiHeader/revisionDesc").delete()
	p = parse.Parser(t, HANDLERS)
	p.dispatch(p.tree.root) 
