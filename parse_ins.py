# For parsing inscriptions.

import os, copy, sys, html
from dharma import tree, parse, config, document, people, langs, biblio

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

def fetch_resp(resp):
	resp = people.plain(resp.removeprefix("part:")) or resp
	return html.escape(resp)

def process_translation(p, div):
	trans = gather_sections(p, div)
	if not trans:
		return
	title = "Translation"
	lang = div["lang"]
	if lang:
		lang = html.escape(langs.from_code(lang) or lang)
		title += f" into {lang}"
	resp = div["resp"]
	if resp:
		title += " by "
		resps = resp.split()
		for i, resp in enumerate(resps):
			if i == 0:
				pass
			elif i < len(resps) - 1:
				title += ", "
			else:
				title += " and "
			title += fetch_resp(resp)
	source = div["source"]
	if source:
		source = biblio.get_ref(source.removeprefix("bib:"), missing=False, rend="default", loc="") or html.escape(source)
		title += f" by {source}"
	trans.title = title
	return trans

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
			if "lang" in div.attrs:
				config.append_unique(p.document.edition_main_langs, div["lang"])
			else:
				for textpart in div.find("//div"):
					if not textpart["type"] == "textpart":
						continue
					if not "lang" in textpart.attrs:
						continue
					config.append_unique(p.document.edition_main_langs, textpart["lang"])
			# XXX Add sec. languages https://github.com/erc-dharma/project-documentation/issues/250
			#and add validity check (in schema?)
			edition = gather_sections(p, div)
			if edition:
				p.document.edition = edition
		elif type == "apparatus":
			p.document.apparatus = gather_sections(p, div)
		elif type == "translation":
			trans = process_translation(p, div)
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

def process_file(path, data):
	t = tree.parse_string(data, path=path)
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
	db = config.db("texts")
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

def export_plain():
	db = config.db("texts")
	renderer = parse.PlainRenderer(strip_physical=True)
	out_dir = config.path_of("plain")
	os.makedirs(out_dir, exist_ok=True)
	for name, path, data in db.execute("""
		select name, printf('%s/%s/%s', ?, repo, path), data
		from texts natural join files where name glob 'DHARMA_INS*'
		""", (config.REPOS_DIR,)):
		print(path)
		try:
			ret = renderer.render(process_file(path, data))
		except tree.Error:
			continue
		out_file = os.path.join(out_dir, name + ".txt")
		with open(out_file, "w") as f:
			f.write(ret)

if __name__ == "__main__":
	path = sys.argv[1]
	data = open(path, "rb").read()
	try:
		doc = process_file(path, data)
		for t, data, params in doc.edition.code:
			document.write_debug(t, data, **params)
		#ret = parse.PlainRenderer().render(doc)
		#sys.stdout.write(ret)
		#export_plain()
	except (KeyboardInterrupt, BrokenPipeError):
		pass
