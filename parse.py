# I initially wanted to do validation and display together, with a real parser,
# possibly bound to rng. But in practice, we need to generate a useful display
# even when texts are not valid. So many files are invalid that being too
# strict would leave us with not much, and even so not being able to display a
# text at all because of a single error would be super annoying.
#
# to make sure we examine everything and to signal stuff we haven't taken into
# account, might want to add a "visited" flag to @. maybe id. for text nodes.

import os, sys, re, io, copy, html, unicodedata
from dharma import prosody, people, tree, gaiji, config, unicode, biblio
from dharma import tree as etree

write = sys.stdout.write

force_color = True
def term_color(code=None):
	if not os.isatty(1) and not force_color:
		return
	if not code:
		write("\N{ESC}[0m")
		return
	code = code.lstrip("#")
	assert len(code) == 6
	R = int(code[0:2], 16)
	G = int(code[2:4], 16)
	B = int(code[4:6], 16)
	write(f"\N{ESC}[38;2;{R};{G};{B}m")

def term_html(): term_color("#5f00ff")
def term_bib(): term_color("#aa007f")
def term_log(): term_color("#008700")
def term_phys(): term_color("#0055ff")
def term_text(): term_color("#aa007f")
def term_span(): term_color("#b15300")
def term_reset(): term_color()

def write_debug(t, data, **params):
	if t == "html":
		term_html()
	elif t == "log":
		term_log()
	elif t == "phys":
		term_phys()
	elif t == "text":
		term_text()
	elif t == "span":
		term_span()
	elif t == "bib" or t == "ref":
		term_bib()
	else:
		assert 0, t
	write("%-04s" % t)
	if data:
		if t in ("text", "html"):
			write(" %r" % data)
		else:
			write(" %s" % data)
	if params:
		for k, v in sorted(params.items()):
			write(" :%s %r" % (k, v))
	term_reset()
	write("\n")

PARA_SEP = chr(1)

def normalize(s):
	if s is None:
		s = ""
	elif not isinstance(s, str):
		# make sure matching doesn't work across array elements
		s = "!!!!!".join(s)
	s = unicodedata.normalize("NFKD", s)
	s = "".join(c for c in s if not unicodedata.combining(c))
	s = s.casefold()
	s = s.replace("œ", "oe").replace("æ", "ae").replace("ß", "ss").replace("đ", "d")
	return unicodedata.normalize("NFC", s.strip())

class Block:

	def __init__(self, name=""):
		self.name = name
		self.code = []
		self.finished = False

	def __repr__(self):
		return "<Block(%s) %r>" % (self.name, self.code)

	def empty(self):
		for cmd, data, params in self.code:
			if cmd == "text" and data == " ":
				continue
			return False
		return True

	def __bool__(self):
		return not self.empty()

	def start_item(self):
		if any(cmd == "text" for cmd, _, _ in self.code):
			self.add_text(PARA_SEP)

	def add_text(self, data):
		if not data:
			return
		data = re.sub(r"\s+", " ", data)
		return self.add_code("text", data)

	def add_html(self, data, **params):
		params.setdefault("plain", True)
		params.setdefault("logical", True)
		params.setdefault("physical", True)
		return self.add_code("html", data, **params)

	def close_line(self, brk):
		i = len(self.code)
		p = i
		while i > 0:
			i -= 1
			rcmd, rdata, rparams = self.code[i]
			if rcmd == "log" and rdata == ">div":
				p = i
				continue
			if rcmd != "phys":
				continue
			if rdata.startswith("="):
				p = i
				continue
			if rdata == "<line":
				self.code.insert(p, ("phys", ">line", {"brk": brk}))
				break

	def add_phys(self, data, **params):
		# XXX handle breaks consistently,trim space always?
		if data != "line":
			assert data.startswith("=")
			self.add_code("phys", data, **params)
			return
		brk = params["brk"]
		self.close_line(brk)
		if not brk:
			i = len(self.code)
			while i > 0:
				i -= 1
				rcmd, rdata, rparams = self.code[i]
				if rcmd == "span" and data == "<" and "dh-space" in rparams["klass"]:
					break
				if rcmd != "text":
					continue
				rdata = rdata.rstrip()
				if not rdata:
					del self.code[i]
					continue
				self.code[i] = (rcmd, rdata, rparams)
				break
		self.add_code("phys", "<line", **params)

	def add_log(self, data, **params):
		self.add_code("log", data, **params)

	def start_span(self, **params):
		params["klass"] = [params["klass"]]
		params["tip"] = [params["tip"]]
		self.add_code("span", "<", **params)

	def end_span(self):
		self.add_code("span", ">")

	def add_code(self, t, data=None, **params):
		rec = (t, data, params)
		self.code.append(rec)

	def finish(self):
		self.close_line(True)
		self.finished = True

	def render_outline(self):
		assert self.finished
		buf = []
		in_head = False
		in_level = 2
		for t, data, params in self.code:
			if t == "log":
				if data == "<head":
					level = params.get("level", 3)
					if level == 6:
						continue # XXX
					in_head = True
					if in_level < level:
						in_level = level
						buf.append("<ul>")
					buf.append(f'<li>')
				elif data == ">head":
					level = params.get("level", 3)
					if level == 6:
						continue # XXX
					in_head = False
					buf.append("</li>")
					if in_level > level:
						in_level = level
						buf.append("</ul>")
			elif t == "phys":
				pass
			elif in_head:
				self.render_common(buf, t, data, params)
		while in_level > 2:
			buf.append("</ul>")
			in_level -= 1
		return "".join(buf)

	def render_common(self, buf, t, data, params):
		if t == "text":
			# TODO be more accurate, only need to hyphenate Indic
			# languages
			if self.name == "edition":
				data = unicode.hyphenate(data)
			text = html.escape(data)
			buf.append(text)
		elif t == "span":
			if data == "<":
				klasses = " ".join(params["klass"])
				tip = " | ".join(params["tip"])
				buf.append('<span class="%s" data-tip="%s">' % (html.escape(klasses), html.escape(tip)))
			elif data == ">":
				buf.append('</span>')
			else:
				assert 0, data
		elif t == "bib":
			ret = biblio.get_entry(data, **params)
			buf.append(ret)
		elif t == "ref":
			ret = biblio.get_ref(data, **params)
			buf.append(ret)
		else:
			assert 0, t

	def render_logical(self):
		assert self.finished
		buf = []
		for t, data, params in self.code:
			if t == "log":
				if data == "<div":
					buf.append('<div class="dh-ed-section">')
				elif data == ">div":
					buf.append('</div>')
				elif data == "<head":
					lvl = params.get("level", 3)
					buf.append('<h%d class="dh-ed-heading">' % lvl)
				elif data == ">head":
					lvl = params.get("level", 3)
					buf.append('</h%d>' % lvl)
				elif data == "<para" or data == "<line":
					if data == "<para" and params.get("rend") == "verse":
						buf.append('<p class="dh-verse">')
					else:
						buf.append("<p>")
				elif data == ">para" or data == ">line":
					buf.append("</p>")
				elif data == "<list":
					typ = params["type"]
					if typ == "plain":
						buf.append('<ul class="dh-list dh-list-plain">')
					elif typ == "bulleted":
						buf.append('<ul class="dh-list">')
					elif typ == "numbered":
						buf.append('<ol class="dh-list">')
					elif typ == "description":
						buf.append('<dl class="dh-list">')
					else:
						assert 0
				elif data == ">list":
					typ = params["type"]
					if typ == "plain":
						buf.append('</ul>')
					elif typ == "bulleted":
						buf.append('</ul>')
					elif typ == "numbered":
						buf.append('</ol>')
					elif typ == "description":
						buf.append('</dl>')
					else:
						assert 0
				elif data == "<verse":
					buf.append('<div class="dh-verse">')
				elif data == ">verse":
					buf.append('</div>')
				elif data == "<item":
					buf.append('<li>')
				elif data == ">item":
					buf.append('</li>')
				elif data == "<key":
					buf.append('<dt>')
				elif data == ">key":
					buf.append('</dt>')
				elif data == "<value":
					buf.append('<dd>')
				elif data == ">value":
					buf.append('</dd>')
				elif data == "=note":
					n = params["n"]
					buf.append(f'<a class="dh-note-ref" href="#note-{n}" id="note-ref-{n}">↓{n}</a>')
				elif data == "<blockquote":
					buf.append('<blockquote>')
				elif data == ">blockquote":
					buf.append('</blockquote>')
				else:
					assert 0, data
			elif t == "phys":
				if data == "<line":
					buf.append('<span class="dh-lb" data-tip="Line start">(%s)</span>' % html.escape(params["n"]))
					if params["brk"]:
						buf.append(" ")
				elif data == ">line":
					pass
				elif data == "=page":
					buf.append('<span class="dh-pagelike" data-tip="Page start">(\N{next page} %s)</span>' % html.escape(params["n"]))
				elif data.startswith("=") and params["type"] == "pagelike":
					unit = html.escape(data[1:].title())
					n = html.escape(params["n"])
					buf.append(f'<span class="dh-pagelike" data-tip="{unit} start">({unit} {n})</span>')
				elif data.startswith("=") and params["type"] == "gridlike":
					unit = html.escape(data[1:].title())
					n = html.escape(params["n"])
					buf.append(f'<span class="dh-gridlike" data-tip="{unit} start">({unit} {n})</span>')
				else:
					assert 0, data
			elif t == "html":
				if params["logical"]:
					buf.append(data)
			else:
				self.render_common(buf, t, data, params)
		return "".join(buf)

	def render_physical(self):
		assert self.finished
		buf = []
		skip = 0
		for t, data, params in self.code:
			if skip > 0:
				if t == "log" and (data == ">head" or data == "<head") and params.get("level"):
					pass
				else:
					continue
			if t == "phys":
				if data == "<line":
					buf.append('<p class="dh-line"><span class="dh-lb" data-tip="Line start">(%s)</span> ' % html.escape(params["n"]))
				elif data == ">line":
					if not params["brk"]:
						buf.append('<span class="dh-hyphen-break" data-tip="Hyphen break">-</span>')
					buf.append('</p>')
				elif data == "=page":
					buf.append('<span class="dh-pagelike" data-tip="Page start">(\N{next page} %s)</span> ' % html.escape(params["n"]))
				elif data.startswith("=") and params["type"] == "pagelike":
					unit = html.escape(data[1:].title())
					buf.append('<span class="dh-pagelike" data-tip="%s start">(%s %s)</span>' % (unit, unit, html.escape(params["n"])))
				elif data.startswith("=") and params["type"] == "gridlike":
					unit = html.escape(data[1:].title())
					buf.append('<span class="dh-gridlike" data-tip="%s start">(%s %s)</span>' % (unit, unit, html.escape(params["n"])))
				else:
					assert 0, data
			elif t == "log":
				if data == "<div":
					buf.append('<div class="dh-ed-section">')
				elif data == ">div":
					buf.append('</div>')
				elif data == "<head":
					if params.get("level"): # verse header
						skip += 1
					else:
						buf.append('<h3 class="dh-ed-heading">')
				elif data == ">head":
					if params.get("level"): # verse header
						skip -= 1
					else:
						buf.append('</h3>')
			elif t == "html":
				if params["physical"]:
					buf.append(data)
			else:
				self.render_common(buf, t, data, params)
		return "".join(buf)

	def searchable_text(self):
		assert self.finished
		buf = []
		for t, data, _ in self.code:
			if not t == "text":
				continue
			buf.append(data)
		return normalize("".join(buf))

class Document:

	tree = None # tree.Tree

	repository = ""
	commit_hash = ""
	commit_date = ""
	last_modified = ""

	ident = ""

	title = None
	author = None
	editors = None
	langs = None
	summary = None

	edition = None
	apparatus = None
	# we can have several translations e.g. DHARMA_INSPallava00002
	translation = None
	commentary = None
	bibliography = None

	xml = ""

	def __init__(self):
		self.langs = []
		self.edition = []
		self.translation = []
		self.sigla = {}
		self.biblio = set()
		self.gaiji = set()
		self.notes = []


class PlainRenderer:

	def __init__(self, strip_physical=True, arlo_normalize=False):
		self.strip_physical = strip_physical
		self.arlo_normalize = arlo_normalize

	def reset(self, buf=""):
		self.buf = buf
		self.indent = 0
		self.list = []

	def add(self, data):
		if len(self.buf) == 0 or self.buf[-1] == "\n":
			data = data.lstrip(" ")
		if self.buf and self.buf[-1] == " ":
			data = data.lstrip(" ")
		if not data:
			return
		if data.strip() and self.buf and self.buf[-1] == "\n":
			self.buf += self.indent * "\t"
		self.buf += data

	def kawi_normalize(self, text):
		text = text.replace("ḥ", "h")
		text = text.replace("ṁ", "ṅ")
		text = text.replace("⌈", "")
		text = text.replace("⌉", "")
		text = text.replace("ə:", "ə̄")
		text = text.replace("Ə:", "Ə̄")
		text = text.replace("·", "")
		text = text.replace("=", "")
		text = text.replace("R\N{combining ring below}", "rə")
		text = text.replace("L\N{combining ring below}", "lə")
		text = text.casefold()
		for vowel in "aiu":
			# Ă, ă, ĭ, etc. -> ā, ā, ī, etc.
			orig = unicodedata.normalize("NFC", vowel + "\N{combining breve}")
			repl = unicodedata.normalize("NFC", vowel + "\N{combining macron}")
			text = text.replace(orig, repl)
		for vowel in "ṛṝḷḹ":
			repl = unicodedata.normalize("NFD", vowel)
			repl = repl.replace("\N{combining dot below}", "\N{combining ring below}")
			repl = unicodedata.normalize("NFC", repl)
			text = text.replace(vowel, repl)
		return text

	def render(self, doc):
		self.reset()
		if doc.title:
			buf = self.buf
			self.reset()
			self.render_block(doc.title)
			titles = "".join(self.buf).split(PARA_SEP)
			self.reset(buf)
			for title in titles:
				self.add(title + "\n")
		else:
			self.add("Untitled\n")
		if doc.editors:
			buf = self.buf
			self.reset()
			self.render_block(doc.editors)
			editors = "".join(self.buf).split(PARA_SEP)
			self.reset(buf)
			if len(editors) > 0:
				self.add("Ed. by %s" % editors[0])
				for editor in editors[1:-1]:
					self.add(", %s" % editor)
				if len(editors) > 1:
					self.add(" and %s" % editors[-1])
			self.add("\n")
		self.add("---\n\n")
		buf = unicodedata.normalize("NFC", self.buf)
		self.reset()
		if doc.edition:
			self.render_block(doc.edition[0])
		text = unicodedata.normalize("NFC", "".join(self.buf).rstrip() + "\n")
		self.reset(buf)
		if self.arlo_normalize:
			text = self.kawi_normalize(text)
		self.add(text)
		return re.sub(r"\n{2,}", "\n\n", self.buf)

	def render_instr(self, t, data, params):
		if t == "log":
			if data == "<div":
				pass
			elif data == ">div":
				pass
			elif data == "<head":
				self.add("\n\n")
				level = params.get("level", 3) - 2
				self.add(level * "#" + " ")
			elif data == ">head":
				self.add("\n\n")
			elif data == "<para":
				pass
			elif data == ">para":
				self.add("\n\n")
			elif data == "<line":
				self.add("\t")
			elif data == ">line":
				self.add("\n")
			elif data == "<verse":
				pass
			elif data == ">verse":
				self.add("\n\n")
			elif data == "<list":
				typ = params["type"]
				if typ == "plain":
					self.list.append("plain")
				elif typ == "bulleted":
					self.list.append("bulleted")
				elif typ == "numbered":
					self.list.append(0)
				elif typ == "description":
					self.list.append("description")
				else:
					assert 0
				self.indent += 1
			elif data == ">list":
				typ = params["type"]
				if typ == "plain":
					pass
				elif typ == "bulleted":
					pass
				elif typ == "numbered":
					pass
				elif typ == "description":
					pass
				else:
					assert 0
				self.list.pop()
				self.indent -= 1
			elif data == "<item":
				if self.list[-1] == "plain":
					pass
				elif self.list[-1] == "bulleted":
					self.add("• ")
				elif self.list[-1] == "description":
					assert 0
				else:
					assert isinstance(self.list[-1], int)
					n = self.list[-1]
					self.add("%d. " % n)
			elif data == ">item":
				self.add("\n")
			elif data == "<key":
				pass
			elif data == ">key":
				self.add(". ")
			elif data == "<value":
				pass
			elif data == ">value":
				self.add("\n")
			elif data == "=note":
				pass
			elif data == "<blockquote":
				self.indent += 1
			elif data == ">blockquote":
				self.indent -= 1
				self.add("\n\n")
			else:
				assert 0, data
		elif t == "text":
			self.add(data)
		elif t == "phys":
			if data == "<line":
				if self.strip_physical and not params["brk"]:
					return
				self.add('(%s)' % params["n"])
				if params["brk"]:
					self.add(" ")
			elif data == ">line":
				pass
			elif data == "=page":
				if self.strip_physical and not params["brk"]:
					return
				self.add('(Page %s)' % params["n"])
			elif data.startswith("=") and params["type"] == "pagelike":
				if self.strip_physical:
					return
				unit = data[1:].title()
				n = params["n"]
				self.add(f'({unit} {n})')
			elif data.startswith("=") and params["type"] == "gridlike":
				if self.strip_physical:
					return
				unit = data[1:].title()
				n = params["n"]
				self.add(f'({unit} {n})')
			else:
				assert 0, data
		elif t == "html":
			if params.get("plain"):
				self.add(html.unescape(data))
		elif t == "span":
			pass
		elif t == "bib":
			ret = biblio.get_entry(data, **params)
			self.add(ret)
		elif t == "ref":
			ret = biblio.get_ref(data, **params)
			self.add(ret)
		else:
			assert 0, t

	def render_block(self, block):
		# Special elements: sic/corr, orig/reg; only keep corr and reg.
		if block is None:
			return
		for t, data, params in block.code:
			self.render_instr(t, data, params)

class Parser:

	tree = None
	div_level = 0

	# For HTML output
	heading_shift = 1

	def __init__(self, tree, handlers):
		self.tree = tree
		self.document = Document()
		self.document.ident = os.path.basename(os.path.splitext(tree.path)[0])
		self.blocks = [Block()]
		self.handlers = handlers
		self.divs = []

	@property
	def top(self):
		return self.blocks[-1]

	def push(self, name):
		b = Block(name)
		self.blocks.append(b)
		return b

	def pop(self):
		b = self.blocks.pop()
		b.finish()
		return b

	@property
	def within_div(self):
		return len(self.divs) > 1

	def add_n(self, n):
		if n != "?" and n in self.divs[-1]:
			return False
		self.divs[-1].add(n)
		return True

	def start_div(self, n="?"):
		# we could duplicate <div in log and phys, for commodity
		self.add_log("<div", n=n)
		self.divs.append(set())

	def end_div(self):
		assert self.within_div
		self.divs.pop()
		self.add_log(">div")

	def add_text(self, text):
		return self.blocks[-1].add_text(text)

	def add_html(self, data, **params):
		return self.blocks[-1].add_html(data, **params)

	def add_phys(self, data, **params):
		return self.blocks[-1].add_phys(data, **params)

	def add_code(self, t, data=None, **params):
		return self.blocks[-1].add_code(t, data, **params)

	def add_log(self, data, **params):
		return self.blocks[-1].add_log(data, **params)

	def start_item(self):
		return self.blocks[-1].start_item()

	def start_span(self, **params):
		return self.blocks[-1].start_span(**params)

	def end_span(self):
		return self.blocks[-1].end_span()

	shorthands = {
		"_": etree.parse_string('<space/>'),
		"|": etree.parse_string('<g type="danda">.</g>'),
		"/": etree.parse_string('<g type="dandaOrnate">.</g>'),
		"||": etree.parse_string('<g type="ddanda">.</g>'),
		"//": etree.parse_string('<g type="ddandaOrnate">.</g>'),
		"@": etree.parse_string('<g type="circle">.</g>'),
		"~": etree.parse_string('<g type="dash">.</g>'),
		# the transliteration shorthand , is recommended for <g type="comma">.</g>
		# yeah but too ambiguous
	}
	shorthands_re = re.compile("(%s)" % "|".join(re.escape(s) for s in sorted(shorthands, key=len, reverse=True)))

	def split_string(self, s):
		for chunk in self.shorthands_re.split(s):
			t = self.shorthands.get(chunk)
			if t:
				self.dispatch(t.root)
			else:
				self.add_text(chunk.replace("'", "’"))

	def dispatch(self, node):
		if node.type in ("comment", "instruction"):
			return
		if node.type == "string":
			self.split_string(str(node))
			return
		assert node.type == "tag"
		f = self.handlers.get(node.name)
		if not f:
			self.complain(node)
			self.add_text(node.text())
			return
		try:
			f(self, node)
		except tree.Error as e:
			self.complain(e)

	def dispatch_children(self, node):
		for child in node:
			self.dispatch(child)

	def complain(self, msg):
		print("UNKNOWN %s" % msg)
		pass

# Like the eponymous function in xslt
def normalize_space(s):
	s = s.strip()
	return re.sub(r"\s+", " ", s)

def parse_lem(p, lem):
	p.dispatch_children(lem)

def parse_ptr(p, ptr):
	ref = ptr["target"]
	if not ref.startswith("bib:"):
		return
	ref = ref.removeprefix("bib:")
	p.add_code("ref", ref, rend="default", loc=[], missing=ref not in p.document.biblio)

def parse_ref(p, ref):
	# TODO
	p.dispatch_children(ref)

def parse_rdg(p, rdg):
	p.start_span(klass="dh-reading", tip="Reading")
	p.dispatch_children(rdg)
	p.end_span()
	sources = [source.removeprefix("bib:") for source in rdg["source"].split()]
	if not sources:
		return
	for ref in sources:
		p.add_text(" ")
		siglum = p.document.sigla.get(ref)
		p.add_code("ref", ref, rend="default", loc=[], siglum=siglum, missing=ref not in p.document.biblio)

def parse_app(p, app):
	loc = app["loc"] or "?"
	p.start_span(klass="dh-lb", tip="Line number")
	p.add_text("(%s)" % loc)
	p.end_span()
	p.add_text(" ")
	lem = app.first("lem")
	if lem:
		p.dispatch(lem)
	rdgs = app.find("rdg")
	if rdgs:
		p.add_text(" \N{white medium diamond} ")
	notes = app.find("note") # we deal with other notes elsewhere
	for i, rdg in enumerate(rdgs):
		p.dispatch(rdg)
		if i < len(rdgs) - 1:
			p.add_text("; ")
		elif not notes:
			p.add_text(".")
	for note in notes:
		p.add_text(" • ")
		p.dispatch_children(note)

def parse_listApp(p, listApp):
	apps = listApp.find("app")
	if not apps:
		return
	prev_loc = None
	for app in apps:
		if prev_loc == app["loc"]:
			p.add_text(" \N{EM DASH} ")
		else:
			if prev_loc is not None:
				p.add_log(">para")
			p.add_log("<para")
		p.dispatch(app)
		prev_loc = app["loc"]
	p.add_log(">para")

def parse_num(p, num):
	# for now we don't deal with @value, @atLeast and @atMost
	p.dispatch_children(num)

# EGD "Additions to the translation"
# EGD "Marking up restored text"
# EGD "The basis of restoration"
supplied_tbl = {
	# EGD: "words added to the translation for the sake of target language
	# syntax"
	"subaudible": ("[]", "Text added to the translation for the sake of target language syntax"),
	# EGD: "words implied by the context and added to the translation for
	# the sake of clarification or disambiguation"
	"explanation": ("()", "Text implied by the context and added to the translation for the sake of clarification or disambiguation"),
	# EGD: "lost" and "omitted" indicate "segments of translation corresponding
	# to text restored by the editor in the original" (they are used both
	# in the edition and in the translation)
	"lost": ("[]", "Lost text"),
	"omitted": ("⟨⟩", "Omitted text"),
	# EGD under "Marking up restored text" says that "undefined" is used when it's not possible
	# to tell whether we have "lost" or "omitted"
	"undefined": ("[]", "Lost or omitted text")
}
# OK
def parse_supplied(p, supplied):
	seps, tip = supplied_tbl.get(supplied["reason"], supplied_tbl["lost"])
	if supplied["cert"] == "low":
		tip += " (low certainty)"
	evidence = supplied["evidence"]
	if evidence == "parallel":
		tip += "; restoration based on previous edition (not assessable)"
	elif tip == "previouseditor":
		tip += "; restoration based on parallel"
	p.start_span(klass="dh-supplied", tip=tip)
	if seps:
		p.add_html(seps[0])
	p.dispatch_children(supplied)
	if seps:
		p.add_html(seps[1])
	p.end_span()

# § Premodern insertion
# OK
add_place_tbl = {
	"inline": "within the same line or in the immediate vicinity of the locus",
	"below": "below the line",
	"above": "above the line",
	"top": "in the top margin",
	"bottom": "in the bottom margin",
	"left": "in the left margin",
	"right": "in the right margin",
	"overstrike": " made in the space where a previous string of text has been erased",
	"unspecified": "(no location information available)",
}
def parse_add(p, node):
	place = node["place"]
	tip = add_place_tbl.get(place, add_place_tbl["unspecified"])
	p.start_span(klass="dh-add", tip=f"Scribal addition {tip}")
	p.add_html("⟨⟨")
	p.dispatch_children(node)
	p.add_html("⟩⟩")
	p.end_span()

# § Premodern deletion
# OK
del_rend_tbl = {
	"strikeout": "text struck through or cross-hatched",
	"ui": "combined application of vowel markers <i>u</i> and <i>i</i> to characters to be deleted",
	"other": "",
	"corrected": "corrected text",
}
def parse_del(p, node):
	tip = del_rend_tbl.get(node["rend"], "")
	if tip:
		tip = f"Scribal deletion ({tip})"
	else:
		tip = "Scribal deletion"
	p.start_span(klass="dh-del", tip=tip)
	p.add_html("⟦")
	p.dispatch_children(node)
	p.add_html("⟧")
	p.end_span()

# § Premodern correction
# OK
def parse_subst(p, subst):
	# (del, add)
	# Use the text of <add> for search
	p.dispatch_children(subst)

# We also deal with notes in <app>
# TODO there are attributes,see EGD
def parse_note(p, note):
	# Avoid nesting notes
	if p.top.name == "note":
		p.dispatch_children(note)
		return
	p.add_log("=note", n=len(p.document.notes) + 1)
	p.push("note")
	p.dispatch_children(note)
	ret = p.pop()
	p.document.notes.append(ret)

def parse_foreign(p, foreign):
	p.add_html("<i>")
	p.dispatch_children(foreign)
	p.add_html("</i>")

# <milestones

def milestone_n(p, node):
	n = node["n"]
	if not n:
		n = "?"
	n = n.replace("_", " ")
	if not p.add_n(n):
		node.bad("@n is not unique")
	return n

def milestone_break(node):
	brk = node["break"]
	if brk not in ("yes", "no"):
		brk = "yes"
	return brk == "yes"

milestone_units = "block column face faces fragment item segment zone".split()

def parse_milestone(p, milestone):
	n = milestone_n(p, milestone)
	brk = milestone_break(milestone)
	unit = milestone["unit"]
	if unit not in milestone_units:
		unit = "column"
	typ = milestone["type"]
	if not typ in ("pagelike", "gridlike"):
		typ = "gridlike"
	p.add_phys("=" + unit, type=typ, n=n, brk=brk)

def parse_lb(p, elem):
	n = milestone_n(p, elem)
	brk = milestone_break(elem)
	# On alignment, EGD §7.5.2
	m = re.match(r"^text-align:\s*(right|center|left|justify)\s*$", elem["style"])
	if m:
		align = m.group(1)
	else:
		align = "left"
	p.add_phys("line", n=n, brk=brk)

def parse_fw(p, fw):
	pass # we deal with it within <pb>

def parse_pb(p, elem):
	n = milestone_n(p, elem)
	brk = milestone_break(elem)
	fw = elem.next
	if fw and fw.name == "fw":
		place = fw["place"]
	else:
		place = ""
	p.add_phys("=page", n=n, brk=brk)
	#p.dispatch_children(fw) TODO

# >milestones

# <editorial

def text_to_html(p, mark):
	block = p.top
	while mark < len(block.code):
		t, data, params = block.code[mark]
		if t == "text":
			block.code[mark] = ("html", html.escape(data), params)
		mark += 1

# OK
def parse_sic(p, sic):
	p.start_span(klass="dh-sic", tip="Incorrect text")
	p.add_html("¿")
	mark = len(p.top.code)
	p.dispatch_children(sic)
	text_to_html(p, mark)
	p.add_html("?")
	p.end_span()

# OK
def parse_corr(p, corr):
	p.start_span(klass="dh-corr", tip="Emended text")
	p.add_html('⟨')
	p.dispatch_children(corr)
	p.add_html('⟩')
	p.end_span()

# OK
def parse_orig(p, orig):
	p.start_span(klass="dh-orig", tip="Non-standard text")
	p.add_html("¡")
	mark = len(p.top.code)
	p.dispatch_children(orig)
	text_to_html(p, mark)
	p.add_html("!")
	p.end_span()

# OK
def parse_reg(p, reg):
	p.start_span(klass="dh-reg", tip="Standardised text")
	p.add_html("⟨")
	p.dispatch_children(reg)
	p.add_html("⟩")
	p.end_span()

# TODO For now there is no nesting of <choice>, but it is allowed in some
# cases. This happens within <orig> and <reg> so must deal with it when parsing
# these tags.
def parse_choice(p, node):
	children = node.children()
	if all(child.name == "unclear" for child in children):
		# <choice>(<unclear>...</unclear>)+</choice>
		# In this case for search just keep the text of the 1st unclear.
		p.start_span(klass="dh-choice-unclear", tip="Unclear (several possible readings)")
		p.add_html("(")
		mark = -1
		for child in children:
			if mark >= 0:
				p.add_html("/")
			p.dispatch_children(child)
			if mark < 0:
				mark = len(p.top.code)
		text_to_html(p, mark)
		p.add_html(")")
		p.end_span()
	else:
		# <choice><sic>...</sic><corr>...</corr></choice>
		# OR
		# <choice><orig>...</orig><reg>...</reg></choice>
		#
		# For searching keep <corr> and <reg>, ignore the rest.
		p.dispatch_children(node) # nothing special to do

# >editorial

# Valid cases are:
#
#	<space [type="semantic"]/> (shorthand is '_')
#	<space [type="semantic"] quantity=... unit="characters"/>
#	<space type="vacat" quantity=... unit="characters"/>
#	<space type="(binding-hole|descender|ascender|defect|feature)"/>
#	<space type="unclassified"/>
#	<space type="unclassified" quantity=... unit="characters"/>
#
# OK
space_types = {
	"semantic": {
		"text": "_",
		"tip": "semantic space",
	},
	"binding-hole": {
		"text": "◯",
		"tip": "binding hole",
	},
	"descender": {
		"text": "⊔",
		"tip": "space left blank in a line because (part of) another character hanging down from the previous line encroaches on the current line",
	},
	"ascender": {
		"text": "⊓",
		"tip": "space left blank in a line because (part of) another (pre-conceived) character popping up from the following line encroaches on the current line",
	},
	"defect": {
		"text": "□",
		"tip": "space; the writing skips a blemish of the surface that was not deliberately created (such as a natural crack or pit, or a fault in the creation of the writing surface)",
	},
	"feature": {
		"text": "_",
		"tip": "space; the writing skips a deliberately created feature (other than binding holes, ascenders and descenders) on the surface (such as engraved artwork, high relief, or a seal attached directly to a copper plate)",
	},
	"vacat": {
		"text": "_",
		"tip": "vacat space; the area was left blank when the rest of the inscription was engraved, possibly with the intent to be filled later on",
	},
	"unclassified": {
		"text": "_",
		"tip": "significant space that does not fit other categories",
	}
}
def parse_space(p, space):
	typ = space["type"]
	if typ not in space_types:
		typ = "semantic"
	if typ in ("semantic", "vacat", "unclassified"):
		quant = space["quantity"]
		if not quant.isdigit():
			quant = "1"
		quant = int(quant)
		if quant < 1:
			quant = 1
		unit = space["unit"]
		if unit != "character":
			unit = "character"
	info = space_types[typ]
	tip = info["tip"]
	text = info["text"]
	if typ in ("semantic", "vacat", "unclassified"):
		if quant < 2:
			s = "small space (from barely noticeable to less than two average character widths in extent)"
		else:
			s = f"large space (about {quant} {unit}s wide)"
		tip = "%s; %s" % (s, tip)
		text *= quant
	p.start_span(klass="dh-space", tip=titlecase(tip))
	p.add_html(text)
	p.end_span()

def parse_abbr(p, node):
	p.start_span(klass="dh-abbr", tip="Abbreviated text")
	p.dispatch_children(node)
	p.end_span()

def parse_ex(p, node):
	p.start_span(klass="dh-abbr-expansion", tip="Abbreviation expansion")
	p.add_html("(")
	p.dispatch_children(node)
	p.add_html(")")
	p.end_span()

def parse_expan(p, node):
	p.dispatch_children(node)

def parse_term(p, node):
	p.dispatch_children(node)

def numberize(s, n):
	last_word = s.split()[-1].lower()
	if last_word not in ("character", "component", "line", "page", "editor"):
		print("cannot numberize term %r" % last_word, file=sys.stderr)
		return s
	if n == 1:
		return s
	return s + "s"

def titlecase(s):
	t = s.split(None, 1)
	t[0] = t[0].title()
	return " ".join(t)

# TODO more styling
def parse_seg(p, seg):
	first = seg.first("*")
	if first and first.name == "gap":
		# We deal with this within parse_gap
		p.dispatch_children(seg)
		return
	rend = seg["rend"].split()
	if "pun" in rend:
		p.start_span(klass="dh-pun", tip="Pun (<i>ślesa</i>)")
		p.add_html("{")
	if "check" in rend:
		p.start_span(klass="dh-check", tip="To check")
	if seg["cert"] == "low":
		p.start_span(klass="dh-check-uncertain", tip="Uncertain segment")
		p.add_html("¿")
	p.dispatch_children(seg)
	if seg["cert"] == "low":
		p.add_html("?")
		p.end_span()
	if "check" in rend:
		p.end_span()
	if "pun" in rend:
		p.add_html("}")
		p.end_span()

# "component" is for character components like vowel markers, etc.; "character" is for akṣaras
# EGD: The EpiDoc element <gap/> ff (full section 5.4)
# EGD: "Scribal Omission without Editorial Restoration"
def parse_gap(p, gap):
	reason = gap["reason"] or "undefined" # most generic choice
	quantity = gap["quantity"]
	precision = gap["precision"]
	extent = gap["extent"] or "unknown"
	unit = gap["unit"] or "character"
	if reason == "ellipsis":
		p.add_html("\N{horizontal ellipsis}", plain=True)
		return
	if reason == "undefined":
		reason = "lost or illegible"
	child = gap.first("certainty")
	if child and child["match"] == ".." and child["locus"] == "name":
		reason = "possibly %s" % reason
	if unit == "component":
		unit = "character component"
	phys_repl = None
	if quantity.isdigit():
		quantity = int(quantity)
		repl = "["
		if precision == "low":
			repl += "ca. "
		if unit == "character":
			if reason == "lost":
				repl += f"{quantity}+"
			elif reason == "illegible":
				repl += f"{quantity}x"
			else:
				# reason = "undefined" (lost or illegible)
				repl += f"{quantity}*"
		elif unit == "character component":
			repl += quantity * "."
		else:
			repl += "%d %s %s" % (quantity, reason, numberize(unit, quantity))
		repl += "]"
		phys_repl = "["
		if precision == "low" and unit != "character":
			phys_repl += "ca. "
		if unit == "character":
			phys_repl += quantity * "*"
		elif unit == "character component":
			phys_repl += quantity * "."
		else:
			phys_repl += "%d %s %s" % (quantity, reason, numberize(unit, quantity))
		phys_repl += "]"
		tip = ""
		if precision == "low":
			tip += "About "
		tip += "%d %s %s" % (quantity, reason, numberize(unit, quantity))
	else:
		if unit == "character":
			repl = "[…]"
		else:
			repl = "[unknown number of %s %s]" % (reason, numberize(unit, +333))
		tip = "Unknown number of %s %s" % (reason, numberize(unit, +333))
	# <seg met="+++-++"><gap reason="lost" quantity="6" unit="character">
	# In this case, keep the tooltip, but display the meter instead of ****, etc.
	parent = gap.parent
	if parent and parent.name == "seg" and parent["met"]:
		met = parent["met"]
		if prosody.is_pattern(met):
			met = prosody.render_pattern(met)
		repl = "[%s]" % met
		phys_repl = None
	p.start_span(klass="dh-gap", tip=tip)
	if phys_repl is not None and phys_repl != repl:
		p.add_html(html.escape(repl), plain=True, physical=False)
		p.add_html(html.escape(phys_repl), plain=True, logical=False)
	else:
		p.add_html(html.escape(repl), plain=True)
	p.end_span()
	# TODO merge consecutive values as in [ca.10x – – – ⏑ – – abc] in editorial

def parse_g(p, node):
	# <g type="...">.</g> for punctuation marks
	# <g type="...">§</g> for space fillers
	# <g type="..."></g> in the other cases viz. for symbols whose functions is unclear
	# The guide talks about subtype, but
	t = node["type"] or "symbol"
	if t == "numeral":
		return p.dispatch_children(node)
	text = node.text()
	if text == ".":
		cat = "punctuation"
	elif text == "§":
		cat = "space-filler"
	else:
		cat = "unclear"
	st = node["subtype"]
	if t == "symbol" and st:
		t = st
	p.document.gaiji.add(t)
	info = gaiji.get(t)
	tip = titlecase(info["description"])
	tip = "%s (category: %s)" % (tip, cat)
	p.start_span(klass="dh-symbol", tip=tip)
	#if info["img"] and not info["prefer_text"]:
	#	p.add_html('<img alt="%s" class="dh-svg" src="%s"/>' % (info["name"], info["img"]))
	#else:
	#	p.add_html(info["text"])
	p.add_text(info["text"])
	p.end_span()

# OK
def parse_unclear(p, node):
	tip = "Unclear text"
	if node["cert"] == "low":
		tip = "Very unclear text"
	reason = node["reason"]
	if reason:
		if reason == "eccentric_ductus":
			reason = f"<i>{reason}</i>"
		tip += " (%s)" % reason.replace("_", " ")
	p.start_span(klass="dh-unclear", tip=tip)
	p.add_html("(")
	p.dispatch_children(node)
	if node["cert"] == "low":
		p.add_html("?")
	p.add_html(")")
	p.end_span()

# EGD "Editorial deletion (suppression)"
def parse_surplus(p, node):
	p.start_span(klass="dh-surplus", tip="Superfluous text erroneously added by the scribe")
	p.add_html("{")
	p.dispatch_children(node)
	p.add_html("}")
	p.end_span()

def parse_p(p, para):
	if para["rend"] == "stanza":
		n = para["n"] or "?"
		if n.isdigit():
			n = to_roman(int(n))
		p.add_log("<head", level=6)
		p.add_html("%s." % n, plain=True)
		p.add_log(">head", level=6)
		p.add_log("<para", rend="verse")
	else:
		p.add_log("<para")
	p.dispatch_children(para)
	p.add_log(">para")

def parse_ab(p, ab):
	p.add_log("<para")
	p.dispatch_children(ab)
	p.add_log(">para")

hi_table = {
	"italic": "i",
	"bold": "b",
	"superscript": "sup",
	"subscript": "sub",
	"check": {"klass": "dh-check"},
	"grantha": {"klass": "dh-grantha", "tip": "Grantha text"},
}
def parse_hi(p, hi):
	rends = hi["rend"].split()
	tags = list(filter(None, (hi_table.get(rend) for rend in rends)))
	for tag in tags:
		if isinstance(tag, str):
			p.add_html("<%s>" % tag)
		else:
			p.start_span(**tag)
	p.dispatch_children(hi)
	tags.reverse()
	for tag in tags:
		if isinstance(tag, str):
			p.add_html("</%s>" % tag)
		else:
			p.end_span()

roman_table = [
	("M", 1000),
	("CM", 900),
	("D", 500),
	("CD", 400),
	("C", 100),
	("XC", 90),
	("L", 50),
	("XL", 40),
	("X", 10),
	("IX", 9),
	("V", 5),
	("IV", 4),
	("I", 1),
]
def to_roman(x):
	if x <= 0 or x > 3000:
		return str(x)
	buf = ""
	for roman, arabic in roman_table:
		while x >= arabic:
			buf += roman
			x -= arabic
	return buf

def parse_lg(p, lg):
	n = lg["n"] or "?"
	if n.isdigit():
		n = to_roman(int(n))
	met = titlecase(lg["met"] or "unknown meter")
	p.add_log("<head", level=6)
	p.add_html("%s. %s" % (n, met), plain=True)
	p.add_log(">head", level=6)
	p.add_log("<verse")
	p.dispatch_children(lg)
	p.add_log(">verse")

def is_description_list(nodes):
	if len(nodes) % 2:
		return False
	for i in range(0, len(nodes), 2):
		label = nodes[i]
		item = nodes[i + 1]
		if label.name != "label" or item.name != "item":
			return False
	return True

def parse_list(p, list):
	typ = list["rend"]
	if typ not in ("plain", "bulleted", "numbered", "description"):
		typ = "plain"
	children = list.children()
	if is_description_list(children): # try to infer it
		typ = "description"
	p.add_log("<list", type=typ)
	if typ == "description":
		# (label, item)*
		for i in range(0, len(children), 2):
			label = children[i]
			item = children[i + 1]
			if label.name != "label" or item.name != "item":
				continue
			p.add_log("<key")
			p.dispatch_children(label)
			p.add_log(">key")
			p.add_log("<value")
			p.dispatch_children(item)
			p.add_log(">value")
	else:
		for item in list.find("item"):
			p.add_log("<item")
			p.dispatch_children(item)
			p.add_log(">item")
	p.add_log(">list", type=typ)

def parse_l(p, l):
	p.add_log("<line")
	p.dispatch_children(l)
	p.add_log(">line")

def extract_bib_ref(p, node):
	assert node.name == "bibl"
	ptr = node.first("ptr")
	if not ptr:
		return None, None
	target = ptr["target"]
	if not target.startswith("bib:"):
		p.complain(ptr)
		return None, None
	ref = target.removeprefix("bib:")
	loc = []
	for r in node.find("citedRange"):
		unit = r["unit"]
		if not unit or unit not in bibl_units:
			unit = "page"
		val = r.text().strip()
		if not val:
			continue
		loc.append((unit, val))
	return ref, loc

bibl_units = set(biblio.cited_range_units)

def parse_listBibl(p, node):
	recs = node.find("bibl")
	if not recs:
		return
	# Avoid displaying "Primary" or "Secondary" if there is nothing there.
	if all(len(rec) == 0 for rec in recs):
		return
	typ = node["type"]
	if typ:
		p.add_log("<head")
		p.add_text(titlecase(typ))
		p.add_log(">head")
	for rec in recs:
		ref, loc = extract_bib_ref(p, rec)
		if not ref:
			# TODO Not legit, still display iy?
			continue
		p.add_code("bib", ref, loc=loc, n=rec["n"])

def parse_bibl(p, node):
	rend = node["rend"]
	if rend not in ("omitname", "ibid", "default"):
		rend = "default"
	ref, loc = extract_bib_ref(p, node)
	if not ref:
		return # TODO
	p.add_code("ref", ref, rend=rend, loc=loc, missing=ref not in p.document.biblio)

def parse_body(p, body):
	for elem in body.children():
		p.dispatch(elem)

def parse_title(p, title):
	p.dispatch_children(title)

def parse_q(p, q):
	if q["rend"] == "block": # TODO other usual values for @rend?
		p.add_log("<blockquote")
		p.dispatch_children(q)
		p.add_log(">blockquote")
	else:
		p.add_html("“")
		p.dispatch_children(q)
		p.add_html("”")

def parse_quote(p, quote):
	return parse_q(p, quote)

def parse_cit(p, cit):
	# <cit>
	#    <quote>the text</quote>
	#    <bibl><ptr target="bib:Agrawala1983_01"/></bibl>
	# </cit>
	#
	# "the text" (Agrawala 1983)
	q = cit.first("quote")
	block = False
	if q and q["rend"] == "block":
		block = True
	if block:
		p.add_log("<blockquote")
	for node in cit.children():
		if node.name == "bibl":
			p.add_text(" (")
			p.dispatch(node)
			p.add_text(")")
		elif node.name == "quote" and block:
			p.dispatch_children(node)
	if block:
		p.add_log(">blockquote")

def remove_duplicates(ls):
	ret = []
	for x in ls:
		if x not in ret:
			ret.append(x)
	return ret

def gather_people(stmt, *paths):
	nodes = [node for path in paths for node in stmt.find(path)]
	nodes.sort(key=lambda node: node.location.start)
	ret = []
	for node in nodes:
		ident = node["ref"]
		if ident and ident.startswith("part:"):
			if ident == "part:jodo":
				continue
			name = people.plain(ident.removeprefix("part:"))
		else:
			name = normalize_space(node.text(space="preserve"))
			if not name:
				continue
		ret.append(name)
	ret = remove_duplicates(ret)
	return ret

def parse_titleStmt(p, stmt):
	p.push("title")
	titles = stmt.find("title")
	for title in titles:
		p.start_item()
		p.dispatch_children(title)
	p.document.title = p.pop()
	p.push("author")
	authors = gather_people(stmt, "author")
	for author in authors:
		p.start_item()
		p.add_text(author)
	p.document.author = p.pop()
	p.push("editors")
	editors = gather_people(stmt, "editor", "principal", "respStmt/persName")
	for editor in editors:
		p.start_item()
		p.add_text(editor)
	p.document.editors = p.pop()

def parse_publicationStmt(p, stmt):
	pass
	# TODO extract the pub place

def parse_roleName(p, node):
	p.dispatch_children(node)

def parse_placeName(p, node):
	p.dispatch_children(node)

def parse_persName(p, node):
	p.dispatch_children(node)

def parse_measure(p, node):
	p.dispatch_children(node)

def parse_date(p, node):
	p.dispatch_children(node)

def parse_sourceDesc(p, desc):
	summ = desc.first("msDesc/msContents/summary")
	if not summ:
		return
	# remove paragraphs
	for para in summ.find(".//p"):
		para.unwrap()
	p.push("summary")
	p.dispatch_children(summ)
	p.document.summary = p.pop()

def parse_facsimile(p, node):
	pass # for images, will see later on

def parse_fileDesc(p, node):
	p.dispatch_children(node)

def parse_teiHeader(p, node):
	p.dispatch_children(node)

def parse_text(p, node):
	p.dispatch_children(node)

def parse_TEI(p, node):
	p.dispatch_children(node)

def make_handlers_map():
	ret = {}
	for name, obj in copy.copy(globals()).items():
		if not name.startswith("parse_"):
			continue
		name = name.removeprefix("parse_")
		ret[name] = obj
	return ret

HANDLERS = make_handlers_map()
