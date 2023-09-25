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
	i = 0
	if children and children[0].name == "head":
		p.push("heading")
		p.dispatch_children(children[0])
		section.heading = p.pop()
		i += 1 # XXX beware, don't ignore stuff!
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
			section = None
			for child in div:
				if child.type == "tag" and child.name == "div":
					if section:
						section.contents = p.pop()
						print("!!pop")
						p.document.edition.append(section)
						section = None
					p.dispatch(child)
				elif child.type not in ("comment", "instruction"):
					if not section:
						section = parse.Section()
						p.push("contents")
					p.dispatch(child)
			if section:
				section.contents = p.pop()
				p.document.edition.append(section)
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

head = """
<!doctype html>
<html lang="en">
<head>
	<meta charset="utf-8">
	<title>foo</title>
	<link rel="preconnect" href="https://fonts.googleapis.com">
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
	<link href="https://fonts.googleapis.com/css2?family=Noto+Sans:ital@0;1&display=swap" rel="stylesheet">
	<link rel="stylesheet" href="style.css">
	<link rel="stylesheet" href="ins-phys.css" id="ins-display">
	<script type="text/javascript" src="ins.js"></script>
</head>
</body>

<button id="phys-btn">Click me</button>
"""
tail = """
</body>
</html>
"""

def process_file(path):
	t = tree.parse(path)
	f = t.first("//teiHeader/encodingDesc")
	if f:
		f.delete()
	f = t.first("//teiHeader/revisionDesc")
	if f:
		f.delete()
	t.first("//publicationStmt").delete()
	p = parse.Parser(t, HANDLERS)
	p.dispatch(p.tree.root)
	with open("out.htm", "w") as f:
		f.write(head)
		f.write('<div class="dh-ed">')
		for section in p.document.edition:
			if section.heading:
				f.write('<h3 class="dh-ed-heading">')
				r = section.heading.render()
				f.write(r)
				f.write('</h3>')
			f.write('<div class="dh-ed-section">')
			r = section.contents.render()
			f.write(r)
			f.write('</div>')
		f.write('</div>')
		f.write(tail)

if __name__ == "__main__":
	if len(sys.argv) > 1:
		process_file(sys.argv[1])
