# For parsing inscriptions.

import copy, sys
from dharma import tree, parse

# Within inscriptions, <div> shouldn't nest, except that we can have
# <div type="textpart"> within <div type="edition">.
# All the DHARMA_INSEC* stuff don't follow the ins schema, too different.
def parse_div(p, div):
	if div["type"] != "textpart":
		p.complain(div)
		return
	n = parse.milestone_n(p, div)
	# rend style subtype
	children = div.children()
	i = 0
	# <head> is supposed to only occur in this context in inscriptions, but
	# in fact we don't really care, might allow it somewhere else
	p.start_div(n=n)
	if children and children[0].name == "head":
		p.add_log("<head")
		p.add_text(n)
		p.add_text(". ")
		p.dispatch_children(children[0])
		p.add_log(">head")
		i += 1
	for child in children[i:]:
		p.dispatch(child)
	p.end_div()

def gather_sections(p, div):
	p.push(div["type"])
	for child in div:
		if child.type == "tag" and child.name == "div":
			if p.within_div:
				p.end_div()
			p.dispatch(child)
		elif child.type not in ("comment", "instruction"):
			if not p.within_div:
				if child.type == "string" and not child.strip():
					continue
				p.start_div()
			p.dispatch(child)
	if p.within_div:
		p.end_div()
	return p.pop()

def gather_biblio(p, body):
	for bibl in body.find("//listBibl/bibl"):
		siglum = bibl["n"]
		ptr = bibl.first("ptr")
		if not ptr:
			continue
		target = ptr["target"]
		if not target.startswith("bib:"):
			continue
		target = target.removeprefix("bib:")
		# TODO add checks
		if siglum:
			p.document.sigla[target] = siglum
		p.document.biblio.add(target)

def parse_body(p, body):
	gather_biblio(p, body)
	for div in body.children():
		type = div["type"]
		if not div.name == "div" or not type in ("edition", "translation", "commentary", "bibliography", "apparatus"):
			p.complain(div)
			continue
		p.divs.clear()
		p.divs.append(set())
		if type == "edition":
			p.document.edition = gather_sections(p, div)
		elif type == "apparatus":
			p.document.apparatus = gather_sections(p, div)
		elif type == "translation":
			trans = gather_sections(p, div)
			if trans:
				p.document.translation.append(trans)
		elif type == "commentary":
			p.document.commentary = gather_sections(p, div)
		elif type == "bibliography":
			p.document.bibliography = gather_sections(p, div)
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

def process_file(file):
	t = tree.parse(file)
	f = t.first("//teiHeader/encodingDesc")
	if f:
		f.delete()
	f = t.first("//teiHeader/revisionDesc")
	if f:
		f.delete()
	f = t.first("//publicationStmt")
	if f:
		f.delete()
	p = parse.Parser(t, HANDLERS)
	p.document.tree = t
	p.dispatch(p.tree.root)
	p.document.xml = tree.html_format(t.first("//body"))
	return p.document

if __name__ == "__main__":
	try:
		doc = process_file(sys.argv[1])
		for t, data, params in doc.edition.code:
			parse.write_debug(t, data, **params)
		#print(doc.edition.render_logical())
	except (KeyboardInterrupt, BrokenPipeError):
		pass
