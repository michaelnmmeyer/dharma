# We could use lxml.etree, xml.etree, or bs4. We don't because we want to track
# accurate file locations (line + column). An annoyance of bs4 is that it tries
# to fix invalid files, this is great for some use cases but we don't want
# that. Using our code is also convenient for adding extra attributes or
# methods to nodes.

# TODO add a node set at the root of the tree to check that we don't attempt to
# insert the same node at several locations; or maybe just duplicate the node
# automatically if we see it's a duplicate. yes, solution 2 is best

# XXX for showing errors when rendering the text, should add to the node that
# poses a problem an "error" attribute that is a non-empty string if the node
# is invalid; we can highlight the node and generate a pop-up or something when
# rendering the text.

import os, re, io, collections, copy
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

# Node types are: Tag, Comment, String, Instruction, Tree. Tree is not really a
# node, but we define it as one nonetheless because we want it to have the same
# basic methods. Tree is the XML document proper: it holds processing
# instructions, the root node, and comments that appear outside of the root
# node. The only reason we need it is precisely so that we can keep track of
# everything that is outside the document's root (in particular processing
# instructions) and can thus reproduce it in full, including comments.

class Node(object):

	type = None # "tree", "tag", "string", "comment", "instruction"
	tree = None # tree this node belongs to
	location = None # (line, column) in the source file
	parent = None

	@property
	def next(self):
		parent = self.parent
		if parent is None:
			return
		i = parent.index(self) + 1
		while i < len(parent):
			if parent[i].type == "tag":
				return parent[i]
			i += 1

	@property
	def prev(self):
		parent = self.parent
		if parent is None:
			return
		i = parent.index(self) - 1
		while i >= 0:
			if parent[i].type == "tag":
				return parent[i]
			i -= 1

	def delete(self):
		parent = self.parent
		if parent:
			return parent.remove(self)
		self.tree = None
		self.parent = None
		self.location = None
		return self

	def replace_with(self, other):
		if not isinstance(other, Tag):
			assert isinstance(other, str)
			other = String(other)
		parent = self.parent
		assert parent is not None
		i = parent.index(self)
		self.delete()
		parent.insert(i, other)
		return self

	def text(self, **kwargs):
		return ""

	def copy(self):
		return copy.deepcopy(self)

class Instruction(Node, dict):

	type = "instruction"

	def __init__(self, target, data):
		self.target = target
		self.data = data or ""
		if self.target != "xml-model":
			return
		# quick 'n dirty parsing just to get the data as a dict
		tree = ElementTree.parse(io.StringIO("<foo %s/>" % self.data))
		root = tree.getroot()
		self.update(root.attrib)

	def __str__(self):
		return "<?%s %s?>" % (self.target, self.data)

	def __repr__(self):
		return str(self)

	def __hash__(self):
		return id(self)

	def xml(self, **kwargs):
		return "<?%s %s?>\n" % (self.target, self.data)

class String(Node, collections.UserString):

	type = "string"

	def clear(self):
		if self.data == "":
			return
		self.location = None
		self.data = ""

	def append(self, data):
		if not data:
			return
		self.location = None
		self.data += data

	def prepend(self, data):
		if not data:
			return
		self.location = None
		self.data = data + self.data

	def insert(self, i, data):
		if not data:
			return
		self.location = None
		if i < 0:
			i += len(self.data)
			if i < 0:
				i = 0
		elif i > len(self.data):
			i = len(self.data)
		self.data = self.data[:i] + data + self.data[i:]

	def xml(self, **kwargs):
		return quote_string(self.data)

	def text(self, **kwargs):
		data = str(self.data) # casting is necessary
		space = kwargs.get("space")
		if not space:
			if self.parent:
				space = self.parent["space"]
			else:
				space = "default"
		if space == "preserve":
			return data
		assert space == "default"
		data = data.strip()
		data = re.sub(r"\s{2,}", " ", data)
		return data

class Comment(String):

	type = "comment"

	def __repr__(self):
		return self.xml()

	def __str__(self):
		return self.xml()

	def xml(self, **kwargs):
		if kwargs.get("strip_comments"):
			return ""
		return "<!-- %s -->" % self.data

	def text(self, **kwargs):
		return ""

namespaced_attrs = {}
namespaced_elems = {}

def remove_namespace(key, type):
	# We use three @ in the xml namespace: @lang, @space, @id.
	# @lang is also a TEI @, but we don't use it. @id and @space
	# are not TEI @. So it's ok to use a single namespace fo
	# everything.
	# Still, we make sure there is no ambiguity.
	colon = key.find(":")
	if colon < 0:
		return key
	short = key[colon + 1:]
	if type == "attr":
		tbl = namespaced_attrs
	else:
		assert type == "elem"
		tbl = namespaced_elems
	have = tbl.get(short)
	if have is not None:
		if have != key:
			raise Exception("ambiguous namespaced %s: %r" % (type, short))
	else:
		tbl[short] = key
	return short

class Branch(Node, list):

	def __hash__(self):
		return id(self)

	def __bool__(self):
		return True

	def __contains__(self, node):
		for child in self:
			if child is node:
				return True
		return False

	def coalesce(self):
		i = 1
		while i < len(self):
			cur = self[i]
			if self[i - 1].type == "string" and cur.type == "string":
				self[i - 1].append(cur)
				del self[i]
				cur.tree = None
				cur.parent = None
				cur.location = None
			else:
				if cur.type == "tag":
					cur.coalesce()
				i += 1

	def index(self, node):
		for i, child in enumerate(self):
			if child is node:
				return i
		raise ValueError("not found")

	def remove(self, node):
		assert node in self
		node.tree = None
		node.parent = None
		node.location = None
		i = self.index(node)
		del self[i]
		if not isinstance(node, Tag):
			return node
		stack = [node]
		while stack:
			root = stack.pop()
			for child in root:
				child.tree = None
				child.location = None
				if isinstance(child, Tag):
					stack.append(child)
		return node

	def children(self, name="*"):
		ret = []
		for node in self:
			if not isinstance(node, Tag):
				continue
			if name == "*" or node.name == name:
				ret.append(node)
		return ret

	def descendants(self, name="*"):
		ret = []
		for node in self:
			if not isinstance(node, Tag):
				continue
			if name == "*" or node.name == name:
				ret.append(node)
			ret.extend(node.descendants(name))
		return ret

	def find(self, path):
		assert len(path) > 0
		if path[0] == "/":
			roots = [self.tree]
			path = path[1:]
		else:
			if path.startswith("./"):
				path = path[2:]
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
			if name == "..":
				roots = unique(root.parent for root in roots if root.parent is not None)
			else:
				roots = [node for root in roots for node in root.children(name)]
			path = path[end + 1:]
		return roots

	def first(self, path):
		ret = self.find(path)
		if ret:
			return ret[0]

	def insert(self, i, node):
		if not isinstance(node, Node):
			assert isinstance(node, str)
			node = String(node)
		if node in self:
			raise Exception("attempt to insert the same (%s) node %r multiple times" % (node.type, node))
		if i < 0:
			i += len(self)
			if i < 0:
				i = 0
		elif i > len(self):
			i = len(self)
		list.insert(self, i, node)
		node.parent = self
		node.tree = self.tree
		node.location = None

	def append(self, node):
		self.insert(len(self), node)

	def prepend(self, node):
		self.insert(0, node)

DEFAULT_LANG = "eng"
DEFAULT_SPACE = "default"

class Tag(Branch):

	type = "tag"
	attrs = None

	def __init__(self, name, attrs):
		self.name = remove_namespace(name, "elem")
		self.attrs = collections.OrderedDict()
		for key, value in attrs:
			self[key] = value

	def __repr__(self):
		ret = "<%s" % self.name
		for k, v in self.attrs.items():
			if isinstance(v, tuple):
				v = "-".join(v)
			ret += ' %s="%s"' % (k, quote_attribute(v))
		ret += ">"
		return ret

	def unwrap(self):
		parent = self.parent
		if not parent:
			raise Exception("attempt to unwrap a root node")
		i = parent.index(self)
		del parent[i]
		for p, node in enumerate(self, i):
			node.parent = parent
			list.insert(parent, p, node)
		self.tree = None
		self.parent = None
		self.location = None
		self.clear()
		return self

	@property
	def path(self):
		buf = []
		node = self
		while True:
			buf.append(node.name)
			node = node.parent
			if not node:
				break
		ret = "/".join(reversed(buf))
		return "/" + ret

	def __getitem__(self, key):
		if isinstance(key, int):
			return list.__getitem__(self, key)
		key = remove_namespace(key, "attr")
		if key != "lang" and key != "space":
			return self.attrs.get(key, "")
		node = self
		while not node.attrs.get(key):
			node = node.parent
			if not node:
				return key == "lang" and DEFAULT_LANG or DEFAULT_SPACE
		return node.attrs[key]

	def __setitem__(self, key, value):
		if isinstance(key, int):
			raise Exception("not supported")
		key = remove_namespace(key, "attr")
		if key == "lang":
			if isinstance(value, str):
				value = value.rsplit("-", 1)
			assert isinstance(value, list) or isinstance(value, tuple)
			assert 1 <= len(value) <= 2
			value = value[0]
		self.attrs[key] = " ".join(value.strip().split())

	def xml(self, **kwargs):
		name = self.name
		if not kwargs.get("remove_namespaces"):
			name = namespaced_elems.get(name, name)
		buf = ["<%s" % name]
		# for now, don't sort attrs for normalization
		for k, v in self.attrs.items():
			if isinstance(v, tuple):
				v = "-".join(v)
			if not kwargs.get("remove_namespaces"):
				k = namespaced_attrs.get(k, k)
			buf.append(' %s="%s"' % (k, quote_attribute(v)))
		if len(self) == 0:
			buf.append("/>")
			return "".join(buf)
		buf.append(">")
		for node in self:
			buf.append(node.xml(**kwargs))
		buf.append("</%s>" % self.name)
		return "".join(buf)

	def text(self, **kwargs):
		buf = []
		for node in self:
			buf.append(node.text(**kwargs))
		return "".join(buf)

class Tree(Branch):

	type = "tree"
	path = None	# path of the XML file (if a file)
	root = None	# might be None
	source = None	# original, unaltered XML source

	def __init__(self):
		self.tree = self

	def __repr__(self):
		if self.path:
			return "<Tree path=%r>" % self.path
		return "<Tree>"

	def xml(self, **kwargs):
		ret = ['<?xml version="1.0" encoding="utf-8"?>\n']
		for node in self:
			ret.append(node.xml(**kwargs))
		return "".join(ret)

	def text(self, **kwargs):
		if self.root:
			return self.root.text(**kwargs)
		return ""

	def delete(self):
		raise Exception("not supported")

	def remove(self, node):
		if node == self.root:
			raise Exception("attempt to delete the tree's root")
		NodeList.remove(self, node)

class Handler(ContentHandler, LexicalHandler, ErrorHandler):

	tree = None
	reader = None

	def setDocumentLocator(self, locator):
		self.locator = locator

	def startDocument(self):
		self.stack = [self.tree]

	def endDocument(self):
		assert self.tree and len(self.stack) == 1

	def startElement(self, name, attrs):
		ordered = ((k, attrs[k]) for k in attrs.getNames())
		tag = Tag(name, ordered)
		tag.location = (self.locator.getLineNumber(), self.locator.getColumnNumber())
		tag.tree = self.tree
		parent = self.stack[-1]
		if parent is not self.tree:
			tag.parent = parent
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
		node = String(data)
		node.location = (self.locator.getLineNumber(), self.locator.getColumnNumber())
		if parent is not self.tree:
			node.parent = parent
		node.tree = self.tree
		list.append(parent, node)

	def comment(self, data):
		parent = self.stack[-1]
		node = Comment(data)
		node.location = (self.locator.getLineNumber(), self.locator.getColumnNumber())
		if parent is not self.tree:
			node.parent = parent
		node.tree = self.tree
		list.append(parent, node)

	def processingInstruction(self, target, data):
		parent = self.stack[-1]
		node = Instruction(target, data)
		node.location = (self.locator.getLineNumber(), self.locator.getColumnNumber())
		if parent is not self.tree:
			node.parent = parent
		node.tree = self.tree
		list.append(parent, node)

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

def parse(f):
	reader = make_parser()
	handler = Handler()
	handler.tree = Tree()
	if isinstance(f, str):
		handler.tree.path = os.path.abspath(f)
		with open(f) as r:
			handler.tree.source = r.read()
	else:
		# file-like
		if hasattr(f, "name"):
			handler.tree.path = os.path.abspath(f.name)
		handler.tree.source = f.read()
	handler.tree.location = (1, 0)
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
