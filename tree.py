# We could use lxml.etree, xml.etree, or bs4. We don't because we want to track
# accurate file locations (line + column). An annoyance of bs4 is that it tries
# to fix invalid files, this is great for some use cases but we don't want
# that. Using our code is also convenient for adding extra attributes or
# methods to nodes.

# XXX for showing errors when rendering the text, should add to the node that
# poses a problem an "error" attribute that is a non-empty string if the node
# is invalid; we can highlight the node and generate a pop-up or something when
# rendering the text.

import os, re, io, collections
from xml.sax import make_parser
from xml.sax.handler import ContentHandler, LexicalHandler, ErrorHandler
from xml.sax.saxutils import escape as quote_string
from xml.sax.xmlreader import XMLReader
from xml.etree import ElementTree

__all__ = ["Error", "parse"]

attribute_tbl = str.maketrans({
	'"': "&quot;",
	"<": "&lt;",
	"&": "&amp;",
})

# We don't use xml.sax.saxutils.quoteattr because it tries to use ' as
# demilitor.
def quote_attribute(s):
	return s.translate(attribute_tbl)

class Error(Exception):

	def __init__(self, node, message):
		self.node = node
		self.message = message

	def __str__(self):
		path, (line, column) = self.node.tree.path, self.node.location
		problem = ["%s:%s:%s: %s" % (path, line, column, self.message)]
		src = self.node.tree.source.splitlines()[line - 1]
		problem.append(src)
		cursor = (column - 1) * " " + "^ here"
		problem.append(cursor)
		return "\n".join(problem)

def unique(items):
	ret = []
	for item in items:
		if not item in ret:
			ret.append(item)
	return ret

NO_LOCATION = (None, None)

# Node types are: Tag, Comment, String, Instruction, Tree. Tree is not really a
# node, but we define it as one nonetheless because we want it to have the same
# basic methods. Tree is the XML document proper: it holds processing
# instructions, the root node, and comments that appear outside of the root
# node. The only reason we need it is precisely so that we can keep track of
# everything that is outside the document's root (in particular processing
# instructions) and can thus reproduce it in full, including comments.

class Node(object):
	type = None
	# The tree this node belongs to.
	tree = None
	# Location in the source file
	location = NO_LOCATION
	# Stuff for navigating the tree. We use the same names as in XPath.
	parent = None # None iff this is the tree itself
	preceding_sibling = None
	following_sibling = None
	preceding = None
	following = None

	def child(self, name):
		if not isinstance(self, Tag) and not isinstance(self, Tree):
			return
		for node in self:
			if not isinstance(node, Tag):
				continue
			if node.name == name:
				return node

	def first_child(self, name=None):
		if not isinstance(self, Tag) and not isinstance(self, Tree):
			return
		for node in self:
			if not isinstance(node, Tag):
				continue
			if name is None or node.name == name:
				return node
			return

	def children(self, name=None):
		if not isinstance(self, Tag) and not isinstance(self, Tree):
			return ret
		for node in self:
			if not isinstance(node, Tag):
				continue
			if name is None or node.name == name:
				yield node

	def descendants(self, name=None):
		if not isinstance(self, Tag) and not isinstance(self, Tree):
			return ret
		for node in self:
			if not isinstance(node, Tag):
				continue
			if name is None or node.name == name:
				yield node
			yield from node.descendants(name)

	def xpath(self, path):
		assert len(path) > 0
		if path[0] == "/":
			roots = [self.tree]
			path = path[1:]
		else:
			roots = [self]
		while path:
			end = path.find("/")
			if end == 0: # have //
				path = path[1:]
				end = path.find("/")
				if end < 0:
					end = len(path)
				name = path[:end]
				path = path[end + 1:]
				roots = [node for root in roots for node in root.descendants(name)]
				continue
			if end < 0:
				end = len(path)
			name = path[:end]
			if name.startswith("@"):
				roots = [root for root in roots if name[1:] in root.attrs]
			elif name == "..":
				roots = unique(root.parent for root in roots if root.parent is not None)
			else:
				roots = [node for root in roots for node in root.children(name)]
			path = path[end + 1:]
		return roots

	def insert(self, i, node):
		if isinstance(node, str) and not isinstance(node, Comment):
			node = String(node)
		assert isinstance(self, Tag) or isinstance(self, Tree)
		if i < 0:
			i += len(self)
			if i < 0:
				i = 0
		elif i > len(self):
			i = len(self)
		prev = i > 0 and self[i - 1] or None
		next = i < len(self) - 1 and self[i + 1] or None
		if node.type == "string":
			if  prev and prev.type == "string":
				prev.append(node)
				return
			if next and next.type == "string":
				next.insert(0, node)
				return
		list.insert(self, i, node)
		if prev:
			prev.following_sibling = node
			prev.following = node
		node.preceding_sibling = prev
		node.preceding = prev
		if next:
			next.preceding_sibling = node
			next.preceding = node
		node.following_sibling = next
		node.following = next
		node.parent = self
		node.tree = self.tree
		node.location = EMPTY_LOCATION

	def _detach(self, tree):
		if self.tree.root == self:
			raise Exception("attempt to delete tree root")
		if self.preceding_sibling:
			self.preceding_sibling.following_sibling = self.following_sibling
		if self.following_sibling:
			self.following_sibling.preceding_sibling = self.preceding_sibling
		if self.preceding:
			self.preceding.following = self.following
		if self.following:
			self.following.preceding = self.preceding
		self.preceding_sibling = None
		self.following_sibling = None
		self.preceding = None
		self.following = None
		self.tree = tree is None and Tree(self) or tree
		self.parent = self.tree
		self.location = EMPTY_LOCATION

	def decompose(self, tree=None):
		assert not isinstance(self, Tree)
		parent = self.parent
		self._detach(tree)
		i = parent.index(self)
		del parent[i]
		if not isinstance(self, Tag):
			return self
		stack = [self]
		while stack:
			node = stack.pop()
			for child in node:
				child.tree = self.tree
				child.location = EMPTY_LOCATION
				if isinstance(child, Tag):
					stack.append(child)
		return self

	def unwrap(self, tree=None):
		assert not isinstance(self, Tree)
		parent = self.parent
		self._detach(tree)
		i = parent.index(self)
		del parent[i]
		assert not self in parent
		if isinstance(self, Tag):
			for i, node in enumerate(self, i):
				parent.insert(i, node)
			self.clear()
		return self

namespaced_attrs = {}

def remove_namespace(key):
	# We use three @ in the xml namespace: @lang, @space, @id.
	# @lang is also a TEI @, but we don't use it. @id and @space
	# are not TEI @. So it's ok to use a single namespace fo
	# everything.
	# Still, we make sure there is no ambiguity.
	colon = key.find(":")
	if colon < 0:
		return key
	short = key[colon + 1:]
	have = namespaced_attrs.get(short)
	if have is not None:
		if have != key:
			raise Exception("ambiguous namespaced attr: %r" % short)
	else:
		namespaced_attrs[short] = key
	return short

class String(Node, collections.UserString):
	type = "string"

	def xml(self):
		return quote_string(self.data)

	def clear(self):
		self.location = NO_LOCATION
		self.data = ""

	def append(self, data):
		self.location = NO_LOCATION
		self.data += data

	def insert(self, i, data):
		self.location = NO_LOCATION
		if i < 0:
			i += len(self.data)
			if i < 0:
				i = 0
		elif i > len(self.data):
			i = len(self.data)
		self.data = self.data[:i] + data + self.data[i:]

	def text(self, **kwargs):
		data = self.data
		space = kwargs.get("space")
		if not space:
			space = self.parent["space"]
		if space == "preserve":
			return data
		assert space == "default"
		data = data.strip()
		data = re.sub(r"\s{2,}", " ", data)
		return data

class Tag(Node, list):
	type = "tag"

	def __init__(self, name, attrs):
		self.name = name
		self.attrs = collections.OrderedDict()
		for key, value in attrs:
			self[key] = value

	def __repr__(self):
		ret = "<%s" % self.name
		for k, v in sorted(self.attrs.items()):
			if isinstance(v, tuple):
				v = "-".join(v)
			ret += ' %s="%s"' % (k, quote_attribute(v))
		ret += ">"
		return ret

	def __getitem__(self, key):
		if isinstance(key, int):
			return list.__getitem__(self, key)
		key = remove_namespace(key)
		if key != "lang" and key != "space":
			return self.attrs[key]
		# XXX what about <foreign> rel. to @lang? also see EGD p. 120
		node = self
		while not node.attrs.get(key):
			node = node.parent
		return node.attrs[key]

	def __setitem__(self, key, value):
		if isinstance(key, int):
			list.__setitem__(self, key, value)
		key = remove_namespace(key)
		if key == "lang":
			if isinstance(value, str):
				value = value.rsplit("-", 1)
			assert isinstance(value, list) or isinstance(value, tuple)
			assert 1 <= len(value) <= 2
			value = value[0]
		self.attrs[key] = value

	def get(self, key, dflt=None):
		assert isinstance(key, str)
		return self.attrs.get(key, dflt)

	def text(self, **kwargs):
		buf = []
		for node in self:
			if node.type in ("string", "tag"):
				buf.append(node.text(**kwargs))
		return "".join(buf)

	def xml(self):
		buf = ["<%s" % self.name]
		# for now, don't sort attrs for normalization
		for k, v in self.attrs.items():
			if isinstance(v, tuple):
				v = "-".join(v)
			buf.append(' %s="%s"' % (namespaced_attrs.get(k, k), quote_attribute(v)))
		if len(self) == 0:
			buf.append("/>")
			return "".join(buf)
		buf.append(">")
		for node in self:
			buf.append(node.xml())
		buf.append("</%s>" % self.name)
		return "".join(buf)

class Comment(String):
	type = "comment"

	def __repr__(self):
		return self.xml()

	def xml(self):
		return "<!-- %s -->" % quote_string(self.data)

class Instruction(Node, dict):
	type = "instruction"

	def __init__(self, target, data):
		self.target = target
		self.data = data or ""
		if self.target != "xml-model":
			return
		tree = ElementTree.parse(io.StringIO("<foo %s/>" % self.data))
		root = tree.getroot()
		self.update(root.attrib)

	def repr(self):
		return "<?%s %s?>" % (self.target, self.data)

	def xml(self):
		return "<?%s %s?>" % (self.target, self.data)

class Tree(Node, list):
	type = "tree"
	path = None	# path of the XML file (if a file)
	root = None	# might be None
	source = None	# original, unaltered XML source

	def __init__(self, root=None):
		self.tree = self
		self.location = (1, 0)
		self.attrs = collections.OrderedDict()
		self.attrs["space"] = "default"
		self.attrs["lang"] = ("eng", "Latn")
		if root is not None:
			self.root = root
			self.append(root)

	def __repr__(self):
		if self.path:
			return "<Tree path=%r>" % self.path
		return "<Tree>"

	def xml(self):
		ret = ['<?xml version="1.0" encoding="utf-8"?>\n']
		for node in self:
			ret.append(node.xml())
		return "".join(ret)

	def text(self, **kwargs):
		if self.root:
			return self.root.text(**kwargs)
		return ""

# For inheritable props (xml:lang, xml:space) and xml:id
def patch_tree(tree):
	def patch_node(node):
		if node.type != "tag":
			return
		have = node.get("lang")
		if have:
			fields = have.rsplit("-", 1)
			if len(fields) == 1:
				node.lang = (fields[0], None)
			else:
				node.lang = tuple(fields)
		space = node.get("space")
		if space:
			node.space = space
		for child in node:
			patch_node(child)
	patch_node(tree.root)

class Handler(ContentHandler, LexicalHandler, ErrorHandler):
	tree = None
	reader = None
	preceding = None

	def chain(self, node):
		if self.preceding:
			self.preceding.following = node
		node.preceding = self.preceding
		self.preceding = node

	def setDocumentLocator(self, locator):
		self.locator = locator

	def startDocument(self):
		self.stack = [self.tree]

	def endDocument(self):
		assert self.tree and len(self.stack) == 1
		patch_tree(self.tree)

	def startElement(self, name, attrs):
		ordered = ((k, attrs[k]) for k in attrs.getNames())
		tag = Tag(name, ordered)
		self.chain(tag)
		tag.location = (self.locator.getLineNumber(), self.locator.getColumnNumber())
		tag.tree = self.tree
		parent = self.stack[-1]
		tag.parent = parent
		if len(parent) > 0:
			parent[-1].following_sibling = tag
			tag.preceding_sibling = parent[-1]
		else:
			tag.preceding_sibling = None
		tag.following_sibling = None
		list.append(parent, tag)
		self.stack.append(tag)

	def endElement(self, name):
		self.tree.root = self.stack.pop()

	def characters(self, data):
		assert len(data) > 0
		parent = self.stack[-1]
		if len(parent) > 0 and parent[-1].type == "string":
			parent[-1].append(data)
			return
		data = String(data)
		data.location = (self.locator.getLineNumber(), self.locator.getColumnNumber())
		self.chain(data)
		data.parent = parent
		data.tree = self.tree
		parent.append(data)

	def comment(self, data):
		parent = self.stack[-1]
		node = Comment(data)
		node.location = (self.locator.getLineNumber(), self.locator.getColumnNumber())
		self.chain(node)
		node.parent = parent
		node.tree = self.tree
		parent.append(node)

	def processingInstruction(self, target, data):
		parent = self.stack[-1]
		node = Instruction(target, data)
		node.location = (self.locator.getLineNumber(), self.locator.getColumnNumber())
		self.chain(node)
		node.parent = parent
		node.tree = self.tree
		parent.append(node)

	def raise_error(self, err):
		# Build a dummy node just to get a formatted location
		node = Node()
		node.tree = self.tree
		node.location = (err.getLineNumber(), err.getColumnNumber())
		raise Error(node, err.getMessage())

	def error(self, err):
		self.raise_error(err)

	def fatalError(self, err):
		self.raise_error(err)

	def warning(self, err):
		self.raise_error(err)

def parse(thing):
	reader = make_parser()
	handler = Handler()
	handler.tree = Tree()
	if isinstance(thing, str):
		handler.tree.path = os.path.abspath(thing)
		with open(thing) as f:
			handler.tree.source = f.read()
	else:
		# file-like
		if hasattr(thing, name):
			handler.tree.path = os.path.abspath(thing.name)
		handler.tree.source = thing.read()
	reader.setContentHandler(handler)
	reader.setErrorHandler(handler)
	reader.setProperty("http://xml.org/sax/properties/lexical-handler", handler)
	handler.reader = reader
	reader.parse(io.StringIO(handler.tree.source))
	return handler.tree

if __name__ == "__main__":
	import sys
	if len(sys.argv) <= 1:
		exit()
	try:
		tree = parse(sys.argv[1])
		print(tree.xml())
	except (BrokenPipeError, KeyboardInterrupt):
		pass
	except Error as err:
		print(err, file=sys.stderr)
