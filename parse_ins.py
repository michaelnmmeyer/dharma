# For parsing inscriptions.

import os, copy, sys
from dharma import tree, parse, config

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
			edition = gather_sections(p, div)
			if edition:
				p.document.edition.append(edition)
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

def process_file(file, db=None):
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
	body = t.first("//body")
	if body:
		p.document.xml = tree.html_format(body)
	if db:
		langs = set()
		for node in t.find("//*"):
			if not "lang" in node.attrs:
				continue
			lang = node["lang"]
			(code,) = db.execute("select ifnull((select id from langs_by_code where code = ?), 'und')", (lang,)).fetchone()
			langs.add(code)
		if not langs:
			langs.add("und")
		p.document.langs = sorted(langs)
	return p.document

def export_arlo_plain_numbered(files):
	renderer = parse.PlainRenderer(strip_physical=False, arlo_normalize=True)
	out_dir = os.path.join(config.THIS_DIR, "arlo_plain", "plain_numbered")
	os.makedirs(out_dir, exist_ok=True)
	for file in files:
		ret = renderer.render(file)
		out_file = os.path.join(out_dir, file.ident + "_numbered.txt")
		with open(out_file, "w") as f:
			f.write(ret)

def export_arlo_plain_raw(files):
	renderer = parse.PlainRenderer(strip_physical=True, arlo_normalize=True)
	out_dir = os.path.join(config.THIS_DIR, "arlo_plain", "plain_raw")
	os.makedirs(out_dir, exist_ok=True)
	for file in files:
		ret = renderer.render(file)
		out_file = os.path.join(out_dir, file.ident + "_raw.txt")
		with open(out_file, "w") as f:
			f.write(ret)

def export_arlo():
	db = config.open_db("texts")
	files = []
	for (name,) in db.execute("""
		select name from documents, json_each(documents.langs)
		where json_each.value = 'kaw' and name glob 'DHARMA_INS*'
		"""):
		path = os.path.join(config.THIS_DIR, "texts", name + ".xml")
		print(path)
		file = process_file(path)
		files.append(file)
	export_arlo_plain_numbered(files)
	export_arlo_plain_raw(files)

def export_plain():
	db = config.open_db("texts")
	renderer = parse.PlainRenderer(strip_physical=True, arlo_normalize=False)
	out_dir = os.path.join(config.THIS_DIR, "plain")
	os.makedirs(out_dir, exist_ok=True)
	for name, path in db.execute("""
		select name, printf('%s/%s/%s', ?, repo, path)
		from texts natural join files where name glob 'DHARMA_INS*'
		""", (config.REPOS_DIR,)):
		print(path)
		try:
			ret = renderer.render(process_file(path))
		except tree.Error:
			continue
		out_file = os.path.join(out_dir, name + ".txt")
		with open(out_file, "w") as f:
			f.write(ret)

if __name__ == "__main__":
	try:
		#doc = process_file(sys.argv[1])
		#for t, data, params in doc.edition[0].code:
		#	parse.write_debug(t, data, **params)
		#ret = parse.PlainRenderer().render(doc)
		#sys.stdout.write(ret)
		#export_arlo()
		export_plain()
	except (KeyboardInterrupt, BrokenPipeError):
		pass
