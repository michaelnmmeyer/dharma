# We could use lxml.etree, xml.etree, or bs4. We don't because we want to track
# accurate file locations. This is not feasible with these libs. Using our own
# code is also convenient for adding attributes or methods to nodes.

import re, io
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

IDS_MAP = {}

# We don't use xml.sax.saxutils.quoteattr because it tries to use ' as
# demilitor.
def quote_attribute(s):
	return s.translate(attribute_tbl)

class Error(Exception):

	def __init__(self, node, message):
		self.node = node
		self.message = message

	def __str__(self):
		path, line, column = self.node.location()
		problem = ["%s:%s:%s: %s" % (path, line, column, self.message)]
		src = self.node.tree.source.splitlines()[line - 1]
		problem.append(src)
		cursor = (column - 1) * " " + "^ here"
		problem.append(cursor)
		return "\n".join(problem)

# Node types are: Tag, Comment, String, Instruction, Tree. Tree is not really a
# node, but we define it as one nonetheless because we want it to have the same
# basic methods. Tree is the XML document proper: it holds processing
# instructions, the root node, and comments that appear outside of the root
# node. The only reason we need it is precisely so that we can keep track of
# everything that is outside the document's root (in particular processing
# instructions) and can thus reproduce it in full, including comments.

class Node(object):
	type = None
	parent = None
	tree = None
	line = None
	column = None
	next = None
	prev = None
	left = None
	right = None
	space = "default"	# xml:space
	lang = ("eng", "Latn")	# xml:lang

	def find(self, name):
		if not isinstance(self, Tag):
			return
		if self.name == name:
			return self
		for node in self:
			if not isinstance(node, Tag):
				continue
			match = node.find(name)
			if match:
				return match

	def child(self, name):
		if not isinstance(self, Tag):
			raise Exception("bad internal call")
		match = None
		for node in self:
			if not isinstance(node, Tag):
				continue
			if node.name == name:
				assert not match
				match = node
		if not match:
			raise Error("expected %r to have a child node %s" % (self, name))
		return match

	def location(self):
		path = self.tree.path or "<none>"
		line = self.line is None and "?" or self.line
		column = self.column is None and "?" or self.column
		return (path, line, column)

class Tag(list, Node):
	type = "tag"

	def __init__(self, name, attrs):
		self.name = name
		self.attrs = dict(attrs)

	def __repr__(self):
		ret = "<%s" % self.name
		for k, v in sorted(self.attrs.items()):
			ret += ' %s="%s"' % (k, quote_attribute(v))
		ret += ">"
		return ret

	def __getitem__(self, key):
		if isinstance(key, int):
			return list.__getitem__(self, key)
		return self.attrs[key]

	def __setitem__(self, key, val):
		if isinstance(key, int):
			list.__setitem__(self, key, value)
		self.attrs[key] = val

	def get(self, key, dflt=None):
		assert isinstance(key, str)
		return self.attrs.get(key, dflt)

	def append(self, node):
		if len(self) > 0:
			self[-1].next = node
			node.prev = self[-1]
		else:
			node.prev = None
		node.next = None
		super().append(node)

	def text(self):
		buf = []
		for node in self:
			if isinstance(node, String) or isinstance(node, Tag):
				buf.append(node.text())
		return "".join(buf)

	def xml(self):
		buf = ["<%s" % self.name]
		for k, v in sorted(self.attrs.items()):
			buf.append(' %s="%s"' % (k, quote_attribute(v)))
		if len(self) == 0:
			buf.append("/>")
			return "".join(buf)
		buf.append(">")
		for node in self:
			buf.append(node.xml())
		buf.append("</%s>" % self.name)
		return "".join(buf)

class String(str, Node):
	type = "string"

	def xml(self):
		return quote_string(self)

	def text(self):
		if self.space == "preserve":
			return self
		assert self.space == "default"
		self = self.strip()
		self = re.sub(r"\s{2,}", " ", self)
		return self

class Comment(str, Node):
	type = "comment"

	def repr(self):
		return self.xml()

	def xml(self):
		return "<!-- %s -->" % quote_string(self)

class Instruction(dict, Node):
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

class Tree(list, Node):
	type = "tree"
	path = None
	root = None
	source = None

	def __init__(self):
		self.tree = self
		self.line = 1
		self.column = 0

	def __repr__(self):
		if self.path:
			return "<Tree path=%r>" % self.path
		return "<Tree>"

	def xml(self):
		ret = ['<?xml version="1.0" encoding="UTF-8"?>']
		for node in self:
			ret.append(node.xml())
		return "\n".join(ret)

	def text(self):
		return self.root.text()

	def find(self, name):
		return self.root.find(name)

# For inheritable props (xml:lang, xml:space) and xml:id
def patch_tree(tree):
	def patch_node(node, lang, space):
		if node.type == "tag":
			have = node.get("xml:lang")
			if have:
				fields = have.rsplit("-", 1)
				if len(fields) == 1:
					lang = (fields[0], None)
				else:
					lang = tuple(fields)
			space = node.get("xml:space", space)
			for child in node:
				patch_node(child, lang, space)
			id = node.get("xml:id")
			if id:
				have = IDS_MAP.get(id)
				if have:
					# XXX not really reliable
					if have.tree.path == node.tree.path and \
						have.line == node.line and \
						have.column == node.column:
						pass
					else:
						raise Error(node, "duplicated id (also found in %r)" % have)
				else:
					IDS_MAP[id] = node
		node.lang = lang
		node.space = space
	patch_node(tree.root, tree.lang, tree.space)

class Handler(ContentHandler, LexicalHandler, ErrorHandler):
	tree = None
	left = None

	def chain(self, node):
		if self.left:
			self.left.right = node
		node.left = self.left
		self.left = node

	def setDocumentLocator(self, locator):
		self.locator = locator

	def startDocument(self):
		self.stack = [self.tree]

	def endDocument(self):
		assert self.tree and len(self.stack) == 1
		patch_tree(self.tree)

	def startElement(self, name, attrs):
		tag = Tag(name, attrs)
		self.chain(tag)
		tag.line = self.locator.getLineNumber()
		tag.column = self.locator.getColumnNumber()
		tag.tree = self.tree
		parent = self.stack[-1]
		tag.parent = parent
		parent.append(tag)
		self.stack.append(tag)

	def endElement(self, name):
		self.tree.root = self.stack.pop()

	def characters(self, data):
		assert len(data) > 0
		parent = self.stack[-1]
		if len(parent) > 0 and isinstance(parent[-1], String):
			prev = parent.pop()
			data = String(prev + data)
			data.line = prev.line
			data.column = prev.column
		else:
			data = String(data)
			data.line = self.locator.getLineNumber()
			data.column = self.locator.getColumnNumber()
		self.chain(data)
		data.parent = parent
		data.tree = self.tree
		parent.append(data)

	def comment(self, data):
		parent = self.stack[-1]
		node = Comment(data)
		node.line = self.locator.getLineNumber()
		node.column = self.locator.getColumnNumber()
		self.chain(node)
		node.parent = parent
		node.tree = self.tree
		parent.append(node)

	def processingInstruction(self, target, data):
		parent = self.stack[-1]
		node = Instruction(target, data)
		node.line = self.locator.getLineNumber()
		node.column = self.locator.getColumnNumber()
		self.chain(node)
		node.parent = parent
		node.tree = self.tree
		parent.append(node)

	def raise_error(self, err):
		# Build a dummy node just to get a formatted location
		node = Node()
		node.tree = self.tree
		node.line = err.getLineNumber()
		node.column = err.getColumnNumber()
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
		handler.tree.path = thing
		with open(thing) as f:
			handler.tree.source = f.read()
	else:
		handler.tree.source = thing.read()
	reader.setContentHandler(handler)
	reader.setErrorHandler(handler)
	reader.setProperty("http://xml.org/sax/properties/lexical-handler", handler)
	reader.parse(io.StringIO(handler.tree.source))
	return handler.tree

if __name__ == "__main__":
	import sys
	if len(sys.argv) <= 1:
		exit()
	try:
		tree = parse(sys.argv[1])
		print(tree.text())
	except (BrokenPipeError, KeyboardInterrupt):
		pass
	except Error as err:
		print(err, file=sys.stderr)
