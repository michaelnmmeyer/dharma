# Internal representation of parsed TEI documents, and code to convert this
# representation to HTML and plain text.
#
# I initially wanted to do validation and display together, with a real parser,
# possibly bound to rng. But in practice, we need to generate a useful display
# even when texts are not valid. So many files are invalid that being too
# strict would leave us with not much, and even so not being able to display a
# text at all because of a single error would be super annoying.
#
# If the idea is to convert texts to many formats, we might want to use
# pandoc's data model. See https://boisgera.github.io/pandoc/document

import os, sys, re, html, unicodedata
from dharma import common, unicode, biblio, tree

# Turns some object (strings, list of strings or None) into a searchable string.
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

# TODO Should merge this with the thing we have for the biblio and with the
# one we have in the parser. Or at least use the same method names.
class Serializer:

	def __init__(self):
		self.tree = tree.Tree()
		self.stack = [self.tree]

	def push(self, node):
		if not isinstance(node, tree.Node):
			node = tree.String(node)
		self.stack.append(node.copy())

	def pop(self):
		assert len(self.stack) > 1
		return self.stack.pop()

	def join(self):
		self.append(self.pop())

	def append(self, node):
		if not isinstance(node, tree.Node):
			node = tree.String(node)
		self.stack[-1].append(node.copy())

	def extend(self, node_iter):
		self.stack[-1].extend(node.copy() for node in node_iter)

class Document:

	def __init__(self):
		self.tree = None # tree.Tree
		# Whether the XML is well-formed.
		self.valid = True
		# XML source code, HTML-encoded.
		self.xml = ""
		self.repository = ""
		# The commit we extracted this file from (not necessarily the latest
		# commit where the file was modified).
		self.commit_hash = ""
		self.commit_date = ""
		# The latest commit that modified this file.
		self.last_modified = ""
		self.last_modified_commit = ""
		# Dharma identifier viz. the file's basename without the extension.
		self.ident = ""
		# Title, summary and hand_desc are all trees.
		self.title = None
		self.summary = None
		self.hand_desc = None
		# All languages used in the document (with @xml:lang), as a list
		# of unique langs.Language objects.
		self.langs = []
		# Like self.langs, but only for languages used in the edition
		# division that do not correspond to a modern, translation-only
		# language.
		self.edition_langs = []
		# One field for each main div.
		self.edition = None
		self.apparatus = None
		self.commentary = None
		self.bibliography = None
		# A single document can have zero or more translations (see e.g.
		# DHARMA_INSPallava00002), so this is a list.
		self.translation = []
		# List of footnotes (<note> element in TEI, except that we
		# don't include here <note> elements from the apparatus because
		# they do not actually represent footnotes; we should probably
		# support notes within notes in the apparatus, because in this
		# case the nesting is justified).
		self.notes = []
		# List of authors (plain strings)
		self.authors = []
		# List of editors (plain strings)
		self.editors = []
		# List of dharma editors ids (the xxxx stuff in "part:xxxx")
		# TODO should merge self.editors with self.editors_ids and have
		# a "Person" object, like we are doin for langs.
		self.editors_ids = []

		## Biblio stuff
		# Map of biblio short titles -> bibliography entries. Only
		# includes bibliography entries that appear in the
		# div[@type='bibliography'].
		self.bib_entries = {}
		# Like bib_entries, but for bibliography entries that are
		# referred to in the file but that do not appear in the
		# div[@type='bibliography'].
		self.external_bib_entries = {}
		# Map of biblio entry short title (string) -> siglum (string)
		self.sigla = {}

		# The following are only used temporarily, while parsing the document.
		# TODO if possible, this should be attached to the Parser object instead.
		self._prosody_entries = {}

	def serialize(self):
		f = Serializer()
		f.push(tree.Tag("document"))
		if self.title:
			f.push(tree.Tag("title"))
			f.extend(self.title)
			f.join()
		for author in self.authors:
			f.push(tree.Tag("author"))
			f.append(author)
			f.join()
		for editor in self.editors:
			f.push(tree.Tag("editor"))
			f.append(editor)
			f.join()
		for editor_id in self.editors_ids:
			f.push(tree.Tag("editor_id"))
			f.append(editor_id)
			f.join()
		if self.summary:
			f.push(tree.Tag("summary"))
			f.extend(self.summary)
			f.join()
		if self.edition:
			f.push(tree.Tag("edition"))
			f.extend(self.edition)
			f.join()
		if self.apparatus:
			f.push(tree.Tag("apparatus"))
			f.extend(self.apparatus)
			f.join()
		for trans in self.translation:
			f.push(tree.Tag("translation"))
			f.extend(trans)
			f.join()
		if self.commentary:
			f.push(tree.Tag("commentary"))
			f.extend(self.commentary)
			f.join()
		if self.bibliography:
			f.push(tree.Tag("bibliography"))
			f.extend(self.bibliography)
			f.join()
		f.join()
		return f.tree

	def html(self, what):
		match what:
			case "title":
				return HTMLRenderer(self.title).render()
			case _:
				raise Exception

class HTMLRenderer(Serializer):

	def __init__(self, root):
		assert root
		self.root = root
		super().__init__()

	def render(self):
		self.render_common(self.root)
		return self.tree

	def render_children(self, node):
		for child in node:
			self.render_common(child)

	def render_common(self, node):
		match node:
			case tree.Tree():
				self.render_children(node)
			case tree.String():
				self.append(node)
			case tree.Tag():
				self.render_tag(node)
			case _:
				pass

	def render_tag(self, node):
		assert isinstance(node, tree.Tag)
		match node.name:
			case "para":
				self.push(tree.Tag("p"))
				for child in node:
					self.render_common(child)
				self.join()
			case "list":
				self.render_list(node)

			case _:
				assert 0, node

	def render_list(self, node):
		match node["type"]:
			case "plain":
				self.push(tree.Tag("ul", class_="list list-plain"))
			case "bulleted":
				self.push(tree.Tag("ul", class_="list"))
			case "numbered":
				self.push(tree.Tag("ol", class_="list"))
		for item in node.find("item"):
			self.push(tree.Tag("li"))
			self.render_children(item)
			self.join()
		self.join()

	def render_dlist(self, node):
		self.push(tree.Tag("dl"))
		for child in node.find("*"):
			match child.name:
				case "key":
					self.push(tree.Tag("dt"))
				case "value":
					self.push(tree.Tag("dd"))
				case _:
					assert 0
			self.render_children(child)
			self.join()
		self.join()


class PlainRenderer:

	def __init__(self, strip_physical=True):
		self.strip_physical = strip_physical

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
			self.add("Ed. by %s" % doc.editors[0])
			for editor in doc.editors[1:-1]:
				self.add(", %s" % editor)
			if len(doc.editors) > 1:
				self.add(" and %s" % doc.editors[-1])
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
				self.add('⟨%s⟩' % params["n"])
				if params["brk"]:
					self.add(" ")
			elif data == ">line":
				pass
			elif data == "{page":
				if self.strip_physical and not params["brk"]:
					return
				self.add('⟨Page %s⟩' % params["n"])
			elif data == "}page":
				pass
			elif data.startswith("=") and params["type"] == "pagelike":
				if self.strip_physical:
					return
				unit = data[1:].title()
				n = params["n"]
				self.add(f'⟨{unit} {n}⟩')
			elif data.startswith("=") and params["type"] == "gridlike":
				if self.strip_physical:
					return
				unit = data[1:].title()
				n = params["n"]
				self.add(f'⟨{unit} {n}⟩')
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
