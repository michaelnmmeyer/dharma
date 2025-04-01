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

def trim_left(strings):
	trimmed = False
	while strings:
		s = strings[0]
		if len(s) == 0 or s.isspace():
			if len(s) > 0:
				trimmed = True
			s.delete()
			del strings[0]
			continue
		if s[0].isspace():
			trimmed = True
			t = tree.String(s.data.lstrip())
			s.replace_with(t)
			strings[0] = t
		break
	return trimmed

def trim_right(strings):
	trimmed = False
	while strings:
		s = strings[-1]
		if len(s) == 0 or s.isspace():
			if len(s) > 0:
				trimmed = True
			s.delete()
			strings.pop()
			continue
		if s[-1].isspace():
			trimmed = True
			t = tree.String(s.data.rstrip())
			s.replace_with(t)
			strings[-1] = t
		break
	return trimmed

def squeeze(strings):
	i = 0
	while i < len(strings):
		s = strings[i]
		if len(s) == 0:
			s.delete()
			del strings[i]
			continue
		ret = re.sub(r"\s+", " ", s.data)
		if ret[0] == " " and i > 0 and strings[i - 1][-1] == " ":
			ret = ret[1:]
		if ret != s.data:
			s.replace_with(tree.String(ret))
			strings[i] = ret
		i += 1

def cleanup_tree(t):
	for node in t.find("//div"):
		for child in node:
			if not isinstance(child, tree.Tag):
				child.delete()
	for node in t.find("//para") + t.find("//head"):
		strings = node.strings()
		trim_left(strings)
		trim_right(strings)
		squeeze(strings)

def cleanup(doc):
	for attr in dir(doc):
		if attr == "tree":
			continue
		value = getattr(doc, attr)
		match value:
			case tree.Tree():
				cleanup_tree(value)
			case list():
				for elem in value:
					if isinstance(elem, tree.Tree):
						cleanup_tree(elem)

class Document:

	def __init__(self):
		self.tree = None # tree.Tree
		# Whether the XML is well-formed.
		self.valid = True
		self.repository = ""
		# Dharma identifier viz. the file's basename without the extension.
		self.identifier = ""
		# XML source code, HTML-encoded.
		self.xml = ""
		# The commit we extracted this file from (not necessarily the latest
		# commit where the file was modified).
		self.commit_hash = ""
		self.commit_date = ""
		# The latest commit that modified this file.
		self.last_modified = ""
		self.last_modified_commit = ""
		# Title, summary and hand are all trees.
		self.title = None
		self.summary = None
		self.hand = None
		# Languages used in the edition division that do not correspond
		# to a modern, translation-only language.
		self.edition_langs = []
		# One field for each main div.
		self.edition = None
		self.apparatus = None
		self.commentary = None
		self.bibliography = None
		# One per display.
		self.edition_full = None
		self.edition_logical = None
		self.edition_physical = None
		# A single document can have zero or more translations (see e.g.
		# DHARMA_INSPallava00002), so this is a list.
		self.translation = []
		# List of footnotes (<note> element in TEI, except that we
		# don't include here <note> elements from the apparatus because
		# they do not actually represent footnotes; we should probably
		# support notes within notes in the apparatus, because in this
		# case the nesting is justified).
		self.notes = []
		# List of authors and of editors. List of tuples
		# (dharma_id, name) where dharma_id is the xxxx stuff in
		# "part:xxxx" and name is a string.  dharma_id can be None
		self.authors = []
		self.editors = []

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
		f = tree.Serializer()
		f.push(tree.Tag("document"))
		f.push(tree.Tag("identifier"))
		f.append(self.identifier)
		f.join()
		f.push(tree.Tag("repository"))
		f.append(self.repository)
		f.join()
		f.push(tree.Tag("valid"))
		f.append(common.from_boolean(self.valid))
		f.join()
		if self.title:
			f.push(tree.Tag("title"))
			f.extend(self.title)
			f.join()
		for author in self.authors:
			f.push(tree.Tag("author"))
			f.append(author)
			f.join()
		for editor_id, editor_name in self.editors:
			f.push(tree.Tag("editor"))
			f.push(tree.Tag("name"))
			f.append(editor_name)
			f.join()
			f.push(tree.Tag("identifier"))
			f.append(editor_id)
			f.join()
			f.join()
		if self.summary:
			f.push(tree.Tag("summary"))
			f.extend(self.summary)
			f.join()
		if self.hand:
			f.push(tree.Tag("hand"))
			f.extend(self.hand)
			f.join()
		f.push(tree.Tag("edition-languages"))
		for lang in self.edition_langs:
			f.push(tree.Tag("language", ident=lang.id))
			f.append(lang.name)
			f.join()
		f.join()
		if self.edition:
			f.push(tree.Tag("edition"))
			head = self.edition.first("head")
			i = self.edition.index(head) + 1
			f.append(head)
			for display in ("logical", "physical", "full"):
				f.push(tree.Tag(display))
				f.extend(self.edition[i:])
				f.join()
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

	def to_html(self):
		from dharma import tohtml
		return tohtml.process(self.serialize())
