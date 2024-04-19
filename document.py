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

class BlockDebugFormatter:

	def __init__(self, write=sys.stdout.write):
		self.write = write
		self.force_color = True

	def format(self, block):
		self.write(f"<Block name={block.name} title={block.title}\n")
		for t, data, params in block.code:
			self.write_debug(t, data, **params)
		self.write(">Block\n")

	def term_color(self, code=None):
		if not os.isatty(1) and not force_color:
			return
		if not code:
			return self.write("\N{ESC}[0m")
		code = code.lstrip("#")
		assert len(code) == 6
		R = int(code[0:2], 16)
		G = int(code[2:4], 16)
		B = int(code[4:6], 16)
		self.write(f"\N{ESC}[38;2;{R};{G};{B}m")

	def term_html(self): self.term_color("#5f00ff")
	def term_bib(self): self.term_color("#aa007f")
	def term_log(self): self.term_color("#008700")
	def term_phys(self): self.term_color("#0055ff")
	def term_text(self): self.term_color("#aa007f")
	def term_span(self): self.term_color("#b15300")
	def term_reset(self): self.term_color()

	def write_debug(self, t, data, **params):
		if t == "html":
			self.term_html()
		elif t == "log":
			self.term_log()
		elif t == "phys":
			self.term_phys()
		elif t == "text":
			self.term_text()
		elif t == "span":
			self.term_span()
		elif t == "bib" or t == "ref":
			self.term_bib()
		else:
			assert 0, t
		self.write("%-04s" % t)
		if data:
			if t in ("text", "html"):
				self.write(" %r" % data)
			else:
				self.write(" %s" % data)
		if params:
			for k, v in sorted(params.items()):
				self.write(" :%s %r" % (k, v))
		self.term_reset()
		self.write("\n")

PARA_SEP = chr(1)

def normalize(s):
	if s is None:
		s = ""
	elif not isinstance(s, str):
		# Make sure matching doesn't work across array elements.
		s = "!!!!!".join(s)
	s = unicodedata.normalize("NFKD", s)
	s = "".join(c for c in s if not unicodedata.combining(c))
	s = s.casefold()
	s = s.replace("œ", "oe").replace("æ", "ae").replace("ß", "ss").replace("đ", "d")
	return unicodedata.normalize("NFC", s.strip())

class Block:

	def __init__(self, name=""):
		self.name = name
		self.title = ""
		self.code = []
		self.finished = False

	def __repr__(self):
		return "<Block(%s) %r>" % (self.name, self.code)

	def __str__(self):
		buf = []
		fmt = BlockDebugFormatter(buf.append)
		fmt.format(self)
		return "".join(buf)

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
		params.setdefault("plain", False)
		params.setdefault("logical", True)
		params.setdefault("physical", True)
		params.setdefault("full", True)
		return self.add_code("html", data, **params)

	def close_line(self, brk):
		# Try to figure out where we should insert an EOL marker
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
			if (rdata.startswith("=") or rdata.startswith("{") or rdata.startswith("}")) and not rparams.get("type") == "gridlike":
				p = i
				continue
			if rdata == "<line":
				self.code.insert(p, ("phys", ">line", {"brk": brk}))
				break

	def add_phys(self, data, **params):
		# XXX handle breaks consistently, trim space always?
		if data != "line":
			assert data.startswith("=") or data.startswith("{") or data.startswith("}")
			self.add_code("phys", data, **params)
			return
		brk = params["brk"]
		self.close_line(brk)
		if not brk:
			i = len(self.code)
			while i > 0:
				i -= 1
				rcmd, rdata, rparams = self.code[i]
				if rcmd == "span" and data == "<" and "space" in rparams["klass"]:
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
		if params.get("tip"):
			params["tip"] = [params["tip"]]
		else:
			params["tip"] = []
		self.add_code("span", "<", **params)

	def end_span(self):
		self.add_code("span", ">")

	def add_code(self, t, data=None, **params):
		rec = (t, data, params)
		self.code.append(rec)

	def finish(self):
		self.close_line(True)
		self.finished = True

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
				klasses = html.escape(" ".join(params["klass"]))
				tip = " | ".join(params["tip"])
				if tip:
					tip = html.escape(tip)
					buf.append(f'<span class="{klasses}" data-tip="{tip}">')
				else:
					buf.append(f'<span class="{klasses}">')
			elif data == ">":
				buf.append('</span>')
			else:
				assert 0, data
		elif t == "bib" or t == "ref":
			buf.append(str(data))
		else:
			assert 0, t

	def render_full(self):
		assert self.finished
		buf = []
		for t, data, params in self.code:
			if t == "log":
				if data == "<div":
					buf.append('<div class="ed-section">')
				elif data == ">div":
					buf.append('</div>')
				elif data == "<head":
					lvl = params.get("level", 3)
					buf.append('<h%d class="ed-heading">' % lvl)
				elif data == ">head":
					lvl = params.get("level", 3)
					buf.append('</h%d>' % lvl)
				elif data == "<para":
					if params.get("rend") == "verse":
						buf.append('<p class="verse">')
					else:
						buf.append("<p>")
				elif data == ">para":
					buf.append("</p>")
				elif data == "<line":
					buf.append('<div class="verse-line">')
					buf.append("<p>")
				elif data == ">line":
					buf.append("</p>")
					buf.append(" <span>%s</span>" % html.escape(params["n"]))
					buf.append("</div>")
				elif data == "<list":
					typ = params["type"]
					if typ == "plain":
						buf.append('<ul class="list list-plain">')
					elif typ == "bulleted":
						buf.append('<ul class="list">')
					elif typ == "numbered":
						buf.append('<ol class="list">')
					elif typ == "description":
						buf.append('<dl class="list">')
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
					if params["numbered"]:
						buf.append('<div class="verse verse-numbered">')
					else:
						buf.append('<div class="verse">')
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
					buf.append(f'<sup><a class="nav-link" href="#note-{n}" id="note-ref-{n}">{n}</a></sup>')
				elif data == "<blockquote":
					buf.append('<blockquote>')
				elif data == ">blockquote":
					buf.append('</blockquote>')
				else:
					assert 0, data
			elif t == "phys":
				if data == "<line":
					if params["brk"]:
						buf.append(" ")
					buf.append('<span class="lb" data-tip="Line start">(%s)</span>' % html.escape(params["n"]))
					if params["brk"]:
						buf.append(" ")
				elif data == ">line":
					pass
				elif data == "{page":
					buf.append('<span class="pagelike" data-tip="Page start">(Page %s)' % html.escape(params["n"]))
				elif data == "}page":
					buf.append("</span>")
				elif data.startswith("=") and params["type"] == "pagelike":
					unit = html.escape(data[1:].title())
					text = f"({unit} {params['n']}"
					if params["label"]:
						text += f": {params['label']}"
					text += ")"
					buf.append('<span class="pagelike" data-tip="%s start">%s</span>' % (unit, html.escape(text)))
				elif data.startswith("=") and params["type"] == "gridlike":
					unit = html.escape(data[1:].title())
					text = f"({unit} {params['n']}"
					if params["label"]:
						text += f": {params['label']}"
					text += ")"
					buf.append('<span class="gridlike" data-tip="%s start">%s</span>' % (unit, html.escape(text)))
				else:
					assert 0, data
			elif t == "html":
				if params["logical"] or params["full"]:
					buf.append(data)
			else:
				self.render_common(buf, t, data, params)
		return "".join(buf)

	def render_logical(self):
		assert self.finished
		buf = []
		for t, data, params in self.code:
			if t == "log":
				if data == "<div":
					buf.append('<div class="ed-section">')
				elif data == ">div":
					buf.append('</div>')
				elif data == "<head":
					lvl = params.get("level", 3)
					buf.append('<h%d class="ed-heading">' % lvl)
				elif data == ">head":
					lvl = params.get("level", 3)
					buf.append('</h%d>' % lvl)
				elif data == "<para":
					if params.get("rend") == "verse":
						buf.append('<p class="verse">')
					else:
						buf.append("<p>")
				elif data == ">para":
					buf.append("</p>")
				elif data == "<line":
					buf.append('<div class="verse-line">')
					buf.append("<p>")
				elif data == ">line":
					buf.append("</p>")
					buf.append(" <span>%s</span>" % html.escape(params["n"]))
					buf.append("</div>")
				elif data == "<list":
					typ = params["type"]
					if typ == "plain":
						buf.append('<ul class="list list-plain">')
					elif typ == "bulleted":
						buf.append('<ul class="list">')
					elif typ == "numbered":
						buf.append('<ol class="list">')
					elif typ == "description":
						buf.append('<dl class="list">')
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
					if params["numbered"]:
						buf.append('<div class="verse verse-numbered">')
					else:
						buf.append('<div class="verse">')
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
					buf.append(f'<sup><a class="nav-link" href="#note-{n}" id="note-ref-{n}">{n}</a></sup>')
				elif data == "<blockquote":
					buf.append('<blockquote>')
				elif data == ">blockquote":
					buf.append('</blockquote>')
				else:
					assert 0, data
			elif t == "phys":
				if data == "<line":
					if params["brk"]:
						buf.append(" ")
					buf.append('<span class="lb" data-tip="Line start">(%s)</span>' % html.escape(params["n"]))
					if params["brk"]:
						buf.append(" ")
				elif data == ">line":
					pass
				elif data == "{page":
					buf.append('<span class="pagelike" data-tip="Page start">(Page %s)' % html.escape(params["n"]))
				elif data == "}page":
					buf.append("</span>")
				elif data.startswith("=") and params["type"] == "pagelike":
					unit = html.escape(data[1:].title())
					text = f"({unit} {params['n']}"
					if params["label"]:
						text += f": {params['label']}"
					text += ")"
					buf.append('<span class="pagelike" data-tip="%s start">%s</span>' % (unit, html.escape(text)))
				elif data.startswith("=") and params["type"] == "gridlike":
					unit = html.escape(data[1:].title())
					text = f"({unit} {params['n']}"
					if params["label"]:
						text += f": {params['label']}"
					text += ")"
					buf.append('<span class="gridlike" data-tip="%s start">%s</span>' % (unit, html.escape(text)))
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
					buf.append('<p class="line"><span class="lb" data-tip="Line start">(%s)</span> ' % html.escape(params["n"]))
				elif data == ">line":
					if not params["brk"]:
						buf.append('<span class="hyphen-break" data-tip="Hyphen break">-</span>')
					buf.append('</p>')
				elif data == "{page":
					buf.append('<div class="pagelike"><span data-tip="Page start">(Page %s) ' % html.escape(params["n"]))
				elif data == "}page":
					buf.append("</span></div>")
				elif data.startswith("=") and params["type"] == "pagelike":
					unit = html.escape(data[1:].title())
					text = f"{unit} {params['n']}"
					if params["label"]:
						text += f": {params['label']}"
					buf.append('<div class="pagelike"><span data-tip="%s start">%s</span></div>' % (unit, html.escape(text)))
				elif data.startswith("=") and params["type"] == "gridlike":
					unit = html.escape(data[1:].title())
					text = f"({unit} {params['n']}"
					if params["label"]:
						text += f": {params['label']}"
					text += ")"
					buf.append('<span class="gridlike" data-tip="%s start">%s</span>' % (unit, html.escape(text)))
				else:
					assert 0, data
			elif t == "log":
				if data == "<div":
					buf.append('<div class="ed-section">')
				elif data == ">div":
					buf.append('</div>')
				elif data == "<head":
					if params.get("level"): # verse header
						skip += 1
					else:
						buf.append('<h3 class="ed-heading">')
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
		return config.normalize_text("".join(buf))

class Document:

	tree = None # tree.Tree

	repository = ""
	commit_hash = ""
	commit_date = ""
	last_modified = ""
	last_modified_commit = ""

	ident = ""

	title = None
	author = None
	editors = None
	editors_ids = None # list of dharma ids (part:XXXX)
	langs = None
	summary = None

	edition = None
	apparatus = None
	# we can have several translations e.g. DHARMA_INSPallava00002
	translation = None
	commentary = None
	bibliography = None
	valid = True

	xml = ""

	def __init__(self):
		self.langs = []
		self.edition = None
		self.translation = []
		self.sigla = {}
		self.biblio = set()
		self.gaiji = set()
		self.notes = []
		self.editors = []
		self.editors_ids = []
		self.bib_entries = {}
		self.edition_langs = []

	def plain_text(self, *args, **kwargs):
		renderer = PlainRenderer(*args, **kwargs)
		return renderer.render(self)


class PlainRenderer:

	def __init__(self, strip_physical=True):
		self.strip_physical = strip_physical

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

	def render(self, doc):
		self.reset()
		if doc.title:
			buf = self.buf
			self.reset()
			self.render_block(doc.title)
			title = self.buf
			self.reset(buf)
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
		self.add(f"URL: https://dharmalekha.info/texts/{doc.ident}\n")
		self.add("---\n\n")
		buf = unicodedata.normalize("NFC", self.buf)
		self.reset()
		if doc.edition:
			self.render_block(doc.edition)
		text = unicodedata.normalize("NFC", "".join(self.buf).rstrip() + "\n")
		self.reset(buf)
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
			elif data == "{page":
				if self.strip_physical and not params["brk"]:
					return
				self.add('(Page %s)' % params["n"])
			elif data == "}page":
				pass
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
			self.add(" ")
			self.add(str(data))
		else:
			assert 0, t

	def render_block(self, block):
		# Special elements: sic/corr, orig/reg; only keep corr and reg.
		if block is None:
			return
		for t, data, params in block.code:
			self.render_instr(t, data, params)
