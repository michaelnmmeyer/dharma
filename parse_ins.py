# For parsing inscriptions.

import copy, sys
from dharma import tree, parse

# Within inscriptions, <div> shouldn't nest, except that we can have
# <div type="textpart"> within <div type="edition">.
# All the DHARMA_INSEC* stuff don't follow the ins schema, too different.
def parse_div(p, div):
	if div["type"] != "textpart":
		print("? %s", div)
		return
	n = parse.milestone_n(div)
	# rend style subtype
	children = div.children()
	i = 0
	# <head> is supposed to only occur in this context in inscriptions, but
	# in fact we don't really care, might allow it somewhere else
	p.add_log("<div", n=n)
	if children and children[0].name == "head":
		p.add_log("<head")
		p.dispatch_children(children[0])
		p.add_text(" ")
		p.add_text(n)
		p.add_log(">head")
		i += 1
	for child in children[i:]:
		p.dispatch(child)
	p.add_log(">div")

# we could duplicate <div in log and phys, for commodity?
def gather_sections(p, div):
	p.push(div["type"])
	within_section = False
	for child in div:
		if child.type == "tag" and child.name == "div":
			if within_section:
				p.add_log(">div")
				within_section = False
			p.dispatch(child)
		elif child.type not in ("comment", "instruction"):
			if not within_section:
				if child.type == "string" and not child.strip():
					continue
				p.add_log("<div")
				within_section = True
			p.dispatch(child)
	if within_section:
		p.add_log(">div")
	return p.pop()

def parse_body(p, body):
	for div in body.children():
		type = div["type"]
		if not div.name == "div" or not type in ("edition", "translation", "commentary"):
			print("? %s" % div)
			continue
		if type == "edition":
			p.document.edition = gather_sections(p, div)
		elif type == "translation":
			trans = gather_sections(p, div)
			p.document.translation.append(trans)
		elif type == "commentary":
			p.document.commentary = gather_sections(p, div)
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
	for rec in p.document.edition.code:
		cmd, data, args = rec
		parse.write_debug(cmd, data, **args)
	p.document.xml = tree.html_format(t.first("//body"))
	return p.document

if __name__ == "__main__":
	try:
		for file in sys.argv[1:]:
			process_file(file)
	except (KeyboardInterrupt, BrokenPipeError):
		pass
