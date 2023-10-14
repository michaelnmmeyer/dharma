# For parsing inscriptions.

import copy, sys
from dharma import tree, parse

def parse_div(p, div):
	type = div["type"]
	assert type == "textpart", div
	n = div["n"]
	assert n, div
	section = p.top_section()
	children = div.children()
	i = 0
	if children and children[0].name == "head":
		p.push("heading")
		p.dispatch_children(children[0])
		section.heading = p.pop()
		i += 1 # XXX we ignore unwrapped text within this div, but we're not supposed to have any _except <lb/pb>!
	p.push("contents")
	for child in children[i:]:
		p.dispatch(child)
	section.contents = p.pop()

def iter_sections(p, div):
	section = None
	for child in div:
		if child.type == "tag" and child.name == "div":
			if section:
				section.contents = p.pop()
				yield section
				section = None
			p.push_section()
			p.dispatch(child)
			yield p.pop_section()
		elif child.type not in ("comment", "instruction"):
			if not section:
				section = parse.Section()
				p.push("contents")
			p.dispatch(child)
	if section:
		section.contents = p.pop()
		yield section

def parse_body(p, body):
	for div in body.children():
		type = div["type"]
		if not div.name == "div" or not type in ("edition", "translation", "commentary"):
			print("? %s" % div)
			continue
		if type == "edition":
			p.document.edition = list(iter_sections(p, div))
		elif type == "translation":
			trans = list(iter_sections(p, div))
			p.document.translation.append(trans)
		elif type == "commentary":
			p.document.commentary = list(iter_sections(p, div))
		else:
			assert 0

def update_handlers_map(m):
	for name, obj in copy.copy(globals()).items():
		if not name.startswith("parse_"):
			continue
		name = name.removeprefix("parse_")
		m[name] = obj

HANDLERS = parse.HANDLERS.copy()
update_handlers_map(HANDLERS)

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
	for section in p.document.edition:
		for rec in section.contents.code:
			cmd, data, args = rec
			parse.write_debug(cmd, data, **args)
		print("-------")
	"""
	for translation in p.document.translation:
		for section in translation:
			for rec in section.contents.code:
				cmd, data, args = rec
				parse.write_debug(cmd, data, **args)
			print("-------")
	"""
	p.document.xml = tree.html_format(t.first("//body"))
	return p.document

if __name__ == "__main__":
	for file in sys.argv[1:]:
		process_file(file)
