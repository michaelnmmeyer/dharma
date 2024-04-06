# TODO add a node set at the root of the tree to check that we don't attempt to
# insert the same node at several locations; or maybe just duplicate the node
# automatically if we see it's a duplicate. yes, solution 2 is best

import os, re, io, collections, copy, sys
from xml.parsers import expat
from xml.sax.handler import ContentHandler, ErrorHandler
from xml.sax.saxutils import escape as quote_string
from xml.sax.xmlreader import XMLReader
from xml.sax.expatreader import create_parser

DEFAULT_LANG = "eng"
DEFAULT_SPACE = "default"

Location = collections.namedtuple("Location", "start end line column")

attribute_tbl = str.maketrans({
	'"': "&quot;",
	"<": "&lt;",
	">": "&gt;",
	"&": "&amp;",
})

# We don't use xml.sax.saxutils.quoteattr because it tries to use ' for
# quoting attributes, and people generally use " instead. We want to preserve
# the original as much as possible.
def quote_attribute(s):
	return '"' + s.translate(attribute_tbl) + '"'

class Error(Exception):

	def __init__(self, line=0, column=0, text="", source=b"", path=""):
		self.path = path
		self.line = line
		self.column = column
		self.text = text
		self.source = source

	def __str__(self):
		return f"Error(path='{self.path}' line={self.line}, column={self.column}, text={repr(self.text)})"

def unique(items):
	ret = []
	for item in items:
		if not item in ret:
			ret.append(item)
	return ret

# Node types are: Tree, Tag, Comment, String, Instruction. None of these is a
# subclass of another, unlike in bs4, where the Comment node is a subclass of
# String. Thus, to check whether a node is a String, we check that
# isinstance(node, String) is true, while in bs4 we need to check both if
# isinstance(node, String) is true and if isinstance(node, Comment) is false.
#
# Tree is the XML document proper, which contains a single tag node and
# optionally comments and processing instructions. The XML tradition is to
# treat the document itself as the root of the tree, while in the DOM
# the document's root is not the document itself but its unique element node,
# viz. <html> in HTML documents.
#
# We follow the second model, mostly out of habit. This means that the tree
# root e.g. <TEI> and other nodes at this level have no parent (node.parent is
# None for them). Still, the Tree node is considered to have children, which
# is weird. Nodes that have been detached from the tree with unwrap() also
# have no parent (nor tree). If we did not use the DOM, we would have to attach
# them all to new trees to keep the behavior consistent.
#
# When parsing documents, we always normalize spaces in attributes: we replace
# all sequences of whitespace characters with " " and we trim whitespace
# from both sides.
#
# We don't deal with XML namespaces at all. We just remove namespace prefixes
# in both elements and attributes. This means that we can't deal with
# documents where namespaces are significant.

class Node(object):

	# Tree this node belongs to. Is None for nodes detached with uwrap().
	tree = None
	# Location object: boundaries of the node in the source code.
	location = None
	# Is None for the root element node and other direct children of the
	# Tree node. Is also None for nodes detached with unwrap().
	parent = None

	def __hash__(self):
		return id(self)

	# A string, one of "tree", "tag", "string", "comment", "instruction".
	@property
	def type(self):
		raise NotImplementedError

	@property
	def source(self):
		if not self.location or not self.tree:
			return
		return self.tree.source[self.location.start:self.location.end].decode()

	# Immediate next sibling node of type "tag". We skip blank text,
	# comments and instructions, but we don't attempt to go past non-blank
	# text. XXX stupid! should have a differentt method for this
	# peculiar use case, we're supposed to return siblings with this one.
	@property
	def next(self):
		parent = self.parent
		if parent is None:
			return
		i = parent.index(self) + 1
		while i < len(parent):
			node = parent[i]
			match node:
				case Tag():
					return node
				case String():
					if node.data and not node.data.isspace():
						return
				case Tree():
					assert 0
			i += 1

	@property
	def prev(self):
		parent = self.parent
		if parent is None:
			return
		i = parent.index(self) - 1
		while i >= 0:
			node = parent[i]
			match node:
				case Tag():
					return node
				case String():
					if node.data and not node.data.isspace():
						return
				case Tree():
					assert 0
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

class Instruction(Node):

	type = "instruction"

	def __init__(self, target, data):
		self.target = target
		self.data = data or ""

	def __bool__(self):
		return True

	def __str__(self):
		return "<?%s %s?>" % (self.target, self.data)

	def __repr__(self):
		return str(self)

	def xml(self, **kwargs):
		return "<?%s %s?>\n" % (self.target, self.data)

class String(Node, collections.UserString):

	# Quirk: string nodes are False when empty, unlike other nodes.
	# OTOH, empty strings are not supposed to appear in a tree that is
	# consolidated.

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
		return quote_string(str(self.data))

	# Per default, we do normalize-space(); to prevent this, use
	# text(space="preserve")
	def text(self, **kwargs):
		data = str(self.data) # casting is necessary for String
		space = kwargs.get("space")
		if not space:
			space = "default"
		elif space == "preserve":
			return data
		data = data.strip()
		data = re.sub(r"\s+", " ", data)
		return data

class Comment(Node, collections.UserString):

	type = "comment"

	def __repr__(self):
		return self.xml()

	def __str__(self):
		return self.xml()

	def __bool__(self):
		return True

	def xml(self, **kwargs):
		if kwargs.get("strip_comments"):
			return ""
		return "<!-- %s -->" % self.data

	def text(self, **kwargs):
		return ""

# Common code for Tree and Tag nodes.
class Branch(Node, list):

	def __bool__(self):
		return True

	# Note that we check for objects identity: we compare pointers instead
	# of using __eq__.
	def __contains__(self, node):
		for child in self:
			if child is node:
				return True
		return False

	# Merge adjacent string nodes
	def coalesce(self):
		i = 0
		while i < len(self):
			cur = self[i]
			if isinstance(cur, String):
				if not cur.data:
					del self[i]
					cur.tree = None
					cur.parent = None
					cur.location = None
				elif i < len(self) - 1 and isinstance(self[i + 1], String):
					next = self[i + 1]
					cur.append(next)
					del self[i + 1]
					next.tree = None
					next.parent = None
					next.location = None
					continue
			elif isinstance(cur, Tag):
				cur.coalesce()
			i += 1

	# Note that we check for objects identity: we compare pointers instead
	# of using __eq__.
	def index(self, node):
		for i, child in enumerate(self):
			if child is node:
				return i
		raise ValueError("not found")

	def remove(self, node):
		assert self.tree.root.parent is None
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

	def children(self, name="*", index=0):
		ret = []
		i = 0
		for node in self:
			if not isinstance(node, Tag):
				continue
			if node.name == name:
				i += 1
			if name == "*" or node.name == name:
				if index == 0 or index == i:
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

	def ancestors(self):
		ret = []
		node = self
		while True:
			node = node.parent
			if not node:
				break
			ret.append(node)
		return ret

	def _split_name_index(self, name):
		m = re.match(r"^(?P<name>[*-.\w]+)(?:\[(?P<index>[0-9]+)\])?$", name)
		assert m, name
		index = m.group("index")
		if index:
			index = int(index)
			assert index > 0, "xpath indexes are one-based"
		else:
			index = 0
		return m.group("name"), index

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
				name, index = self._split_name_index(path[:end])
				assert index == 0, "cannot use indexes when looking for descendants"
				path = path[end + 1:]
				roots = [node for root in roots for node in root.descendants(name)]
				continue
			if end < 0:
				end = len(path)
			name, index = self._split_name_index(path[:end])
			if name == ".":
				pass
			elif name == "..":
				roots = unique(root.parent for root in roots if root.parent is not None)
			else:
				roots = [node for root in roots for node in root.children(name, index)]
			path = path[end + 1:]
		return roots

	def first(self, path):
		ret = self.find(path)
		if ret:
			return ret[0]

	def insert(self, i, node):
		if not isinstance(node, Node):
			assert isinstance(node, str), "%r" % node
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

class Tag(Branch):

	type = "tag"
	attrs = None

	def __init__(self, name, *args, **kwargs):
		self.name = name
		self.attrs = collections.OrderedDict()
		self.problems = []
		if args:
			assert len(args) == 1
			assert not kwargs
			(attrs,) = args
			if isinstance(attrs, dict):
				attrs = attrs.items()
		else:
			attrs = kwargs.items()
		for key, value in attrs:
			self[key] = value

	def __repr__(self):
		ret = "<%s" % self.name
		for k, v in self.attrs.items():
			ret += ' %s=%s' % (k, quote_attribute(v))
		ret += ">"
		return ret

	def __hash__(self):
		return id(self)

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

	def bad(self, msg):
		self.problems.append(msg)
		if self.tree:
			self.tree.bad_nodes.add(self)

	@property
	def path(self):
		buf = []
		node = self
		while node:
			parent = node.parent
			if parent:
				index = parent.children(node.name).index(node) + 1
			else:
				index = 1
			buf.append((node.name, index))
			node = parent
		buf.reverse()
		return "".join("/%s[%d]" % p for p in buf)

	def __eq__(self, other):
		return id(self) == id(other)

	def __getitem__(self, key):
		if isinstance(key, int):
			return list.__getitem__(self, key)
		return self.attrs.get(key, "")

	def __setitem__(self, key, value):
		if isinstance(key, int):
			raise NotImplementedError
		# Always normalize space.
		value = " ".join(str(value).strip().split())
		self.attrs[key] = value

	def __delitem__(self, key):
		if isinstance(key, int):
			list.__delitem__(self, key)
			return
		try:
			del self.attrs[key]
		except KeyError:
			pass

	def xml(self, **kwargs):
		name = self.name
		buf = ["<%s" % name]
		# For now, don't sort attrs for normalization.
		for k, v in self.attrs.items():
			buf.append(' %s=%s' % (k, quote_attribute(v)))
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
	file = None	# path of the XML file (if a file)
	path = "/"
	root = None	# might be None
	# XML source, in bytes, encoded as UTF-8
	source = None

	def __init__(self):
		self.tree = self
		self.bad_nodes = set()

	def __repr__(self):
		if self.file:
			return "<Tree file=%r>" % self.file
		return "<Tree>"

	def xml(self, **kwargs):
		ret = []
		for node in self:
			ret.append(node.xml(**kwargs))
		return "".join(ret)

	def tag(self, name, *args, **kwargs):
		tag = Tag(name, *args, **kwargs)
		tag.tree = self
		return tag

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

	replace_with = None
	next = None
	prev = None

class Parser:

	def __init__(self, source, path=None):
		self.parser = expat.ParserCreate()
		self.parser.ordered_attributes = 1
		for attr in dir(self):
			if not attr[0].isupper():
				continue
			val = getattr(self, attr)
			if not callable(val):
				continue
			setattr(self.parser, attr, val)
		self.tree = Tree()
		self.stack = [self.tree]
		self.tree.source = source
		self.tree.file = path
		self.tree.location = Location(0, len(source), 1, 1)
		self.last_node = None

	def parse(self):
		self.parser.Parse(self.tree.source, True)
		if self.last_node:
			loc = self.last_node.location
			self.last_node.location = Location(loc.start, len(self.tree.source), loc.line, loc.column)
		return self.tree

	def set_location(self, node, close=False):
		start = self.parser.CurrentByteIndex
		if self.last_node is not None:
			last = self.last_node.location
			self.last_node.location = Location(last.start, start, last.line, last.column)
		if not close:
			line = self.parser.CurrentLineNumber
			column = self.parser.CurrentColumnNumber
			node.location = Location(start, None, line, column)
		self.last_node = node

	def make_node(self, klass, *args):
		node = klass(*args)
		node.tree = self.tree
		parent = self.stack[-1]
		if parent is not self.tree:
			node.parent = parent
		list.append(parent, node)
		if klass is Tag:
			self.stack.append(node)
		self.set_location(node)

	def XmlDeclHandler(self, version, encoding, standalone):
		data = ""
		if version is not None:
			data += " version=" + quote_attribute(version)
		if encoding is not None:
			data += " encoding=" + quote_attribute(encoding)
		if standalone != -1:
			data += " standalone=" + quote_attribute(standalone and "yes" or "no")
		self.make_node(Instruction, "xml", data[1:])

	def StartDoctypeDeclHandler(self, doctypeName, systemId, publicId, has_internal_subset):
		raise NotImplementedError

	def EndDoctypeDeclHandler(self):
		raise NotImplementedError

	def ElementDeclHandler(self, name, model):
		raise NotImplementedError

	def AttlistDeclHandler(self, elname, attname, type, default, required):
		raise NotImplementedError

	def StartElementHandler(self, name, attributes):
		# Drop all namespaces.
		colon = name.find(":")
		if colon >= 0:
			name = name[colon + 1:]
		attrs = []
		for i in range(0, len(attributes), 2):
			key, value = attributes[i:i + 2]
			colon = key.find(":")
			if colon >= 0:
				key = key[colon + 1:]
			if key == "lang":
				# san-Latn -> san
				value = value.rsplit("-", 1)[0]
			attrs.append((key, value))
		self.make_node(Tag, name, attrs)

	def EndElementHandler(self, name):
		node = self.stack.pop()
		self.tree.root = node
		self.set_location(node, close=True)

	def ProcessingInstructionHandler(self, target, data):
		self.make_node(Instruction, target, data)

	def CharacterDataHandler(self, data):
		assert len(data) > 0
		parent = self.stack[-1]
		if len(parent) > 0 and isinstance(parent[-1], String):
			# need to save the location because we set it to None
			# when the string is modified
			loc = parent[-1].location
			parent[-1].append(data)
			parent[-1].location = loc
		else:
			self.make_node(String, data)

	def EntityDeclHandler(self, entityName, is_parameter_entity, value, base, systemId, publicId, notationName):
		raise NotImplementedError

	def NotationDeclHandler(self, notationName, base, systemId, publicId):
		raise NotImplementedError

	def StartNamespaceDeclHandler(self, prefix, uri):
		raise NotImplementedError

	def EndNamespaceDeclHandler(self, prefix):
		raise NotImplementedError

	def CommentHandler(self, data):
		self.make_node(Comment, data)

	def StartCdataSectionHandler(self):
		raise NotImplementedError

	def EndCdataSectionHandler(self):
		raise NotImplementedError

	def DefaultHandler(self, data):
		if data.strip():
			raise NotImplementedError
		self.CharacterDataHandler(data)

	def NotStandaloneHandler(self):
		raise NotImplementedError

	def ExternalEntityRefHandler(self, context, base, systemId, publicId):
		raise NotImplementedError

def parse_string(source, **kwargs):
	if isinstance(source, str):
		source = source.encode()
	try:
		return Parser(source, **kwargs).parse()
	except expat.ExpatError as e:
		err = e
	# https://docs.python.org/3/library/pyexpat.html#xml.parsers.expat.XMLParserType
	# err.offset counts columns from 0
	raise Error(kwargs.get("path", "<memory>"),
		line=err.lineno, column=err.offset + 1,
		text=expat.errors.messages[err.code], source=source)

# file can be either a file-like object or a string
def parse(file, **kwargs):
	if hasattr(file, "read"):
		# assume file-like
		source = file.read()
		if not kwargs.get("path") and file is not sys.stdin and hasattr(file, "name"):
			kwargs["path"] = os.path.abspath(str(file.name))
	else:
		with open(file, "rb") as f:
			source = f.read()
		if not kwargs.get("path"):
			kwargs["path"] = os.path.abspath(file)
	return parse_string(source, **kwargs)

def term_color(code=None):
	if not code:
		return "\N{ESC}[0m"
	code = code.lstrip("#")
	assert len(code) == 6
	R = int(code[0:2], 16)
	G = int(code[2:4], 16)
	B = int(code[4:6], 16)
	return f"\N{ESC}[38;2;{R};{G};{B}m"

colors = {
	"instruction": "#aa5500",
	"comment": "#3b9511",
	"tag": "#0055ff",
	"attr-name": "#5500ff",
	"attr-value": "#5500ff",
}

def space_before_opening(node):
	assert isinstance(node, Tag)
	parent = node.parent
	if not parent:
		return False
	i = parent.index(node) - 1
	while i >= 0:
		if parent[i].type == "string":
			if parent[i].rstrip() != parent[i]:
				return True
			if parent[i] != "":
				return False
		elif parent[i].type not in ("comment", "instruction"):
			return False
		i -= 1
	return False

def space_after_opening(node):
	assert isinstance(node, Tag)
	i = 0
	while i < len(node):
		if node[i].type == "string":
			if node[i].lstrip() != node[i]:
				return True
			if node[i] != "":
				return False
		elif node[i].type not in ("comment", "instruction"):
			return False
		i += 1
	return False

def space_before_closing(node):
	assert isinstance(node, Tag)
	i = len(node)
	while i > 0:
		i -= 1
		if node[i].type == "string":
			if node[i].rstrip() != node[i]:
				return True
			if node[i] != "":
				return False
		elif node[i].type not in ("comment", "instruction"):
			return False
	return False

def space_after_closing(node):
	assert isinstance(node, Tag)
	parent = node.parent
	if not parent:
		return False
	i = parent.index(node) + 1
	while i < len(parent):
		match parent[i]:
			case String() if node.data and not node.data.isspace():
				if parent[i].lstrip() != parent[i]:
					return True
				if parent[i] != "":
					return False
			case Comment() | Instruction():
				pass
			case _:
				return False
		i += 1
	return False


class Formatter:

	def __init__(self, html=True, pretty=True, strip_comments=True,
		color=False, max_width=80 ** 10, indent_string=2 * " "):
		# max_width is soft, not hard.
		self.indent = 0
		self.offset = 0
		self.buf = io.StringIO()
		self.html = html
		self.pretty = pretty
		self.strip_comments = strip_comments
		self.color = color
		self.max_width = max_width
		self.indent_string = indent_string

	def format(self, node):
		match node:
			case Tree():
				return self.format_tree(node)
			case Tag():
				return self.format_tag(node)
			case String():
				return self.format_string(node)
			case Comment():
				return self.format_comment(node)
			case Instruction():
				return self.format_instruction(node)
			case _:
				assert 0

	def format_tree(self, node):
		for child in node:
			self.format(child)

	def format_instruction(self, node):
		self.write("<?%s %s?>" % (node.target, node.data), klass="instruction")
		if self.pretty:
			self.write("\n")

	def format_comment(self, node):
		if self.strip_comments:
			return
		node = node.data
		if not self.pretty:
			self.write(f"<!--{node}-->", klass="comment")
			return
		if self.pretty:
			lines = node.splitlines()
			if len(lines) == 1:
				self.write(f"<!--{lines[0]}-->", klass="comment")
			else:
				self.write("<!--")
				for line in lines:
					self.write(line, klass="comment")
					self.write("\n")
				self.write("-->")

	def format_string(self, node):
		node = str(node)
		if not self.pretty:
			self.write(quote_string(node))
			return
		text = re.sub(r"\s+", " ", node.strip())
		if not text:
			return
		for i, token in enumerate(text.split()):
			if i > 0 and self.offset + 1 + len(token) > self.max_width:
				self.write("\n")
			elif i > 0:
				self.write(" ")
			self.write(quote_string(token))

	def format_opening_tag(self, node):
		self.write("<", klass="tag")
		self.write(node.name, klass="tag")
		attrs = node.attrs.items()
		if self.pretty:
			# We might want to sort tags in different ways,
			# depending on the tag name, for readability and to
			# follow people's habits
			attrs = sorted(attrs)
		for k, v in attrs:
			if k in ("lang", "space", "base", "id"):
				k = f"xml:{k}" # HACK
			self.write(" ")
			self.write("%s" % k, klass="attr-name")
			self.write("=")
			self.write('%s' % quote_attribute(v), klass="attr-value")
		if len(node) == 0: # might also have non-consodilated nodes XXX
			self.write("/>", klass="tag")
		else:
			self.write(">", klass="tag")

	def format_closing_tag(self, node):
		if len(node) == 0:
			return
		self.write("</", klass="tag")
		self.write("%s" % node.name, klass="tag")
		self.write(">", klass="tag")

	def format_tag(self, node):
		if not self.pretty:
			self.format_opening_tag(node)
			for child in node:
				self.format(child)
			self.format_closing_tag(node)
			return
		if space_before_opening(node) and not self.wrote_space():
			if space_after_opening(node) and space_before_closing(node):
				self.write("\n")
			else:
				self.write("\n")
		self.format_opening_tag(node)
		if space_after_opening(node) and space_before_closing(node):
			self.write("\n")
			self.indent += 1
			for child in node:
				self.format(child)
			self.indent -= 1
			self.write("\n")
		else:
			self.indent += 1
			for child in node:
				self.format(child)
			self.indent -= 1
		self.format_closing_tag(node)

	def write(self, text, klass=None):
		if klass:
			if self.html:
				self.buf.write('<span class="%s">' % klass)
			elif self.color:
				self.buf.write(term_color(colors[klass]))
		if self.pretty:
			assert text == "\n" or not "\n" in text
			if text == "\n":
				self.buf.write("\n")
				self.offset = 0
			else:
				if self.offset == 0:
					self.offset += self.buf.write(
						self.indent_string * self.indent)
				if self.html:
					self.buf.write(quote_string(text))
				else:
					self.buf.write(text)
				self.offset += len(text)
		else:
			if self.html:
				self.buf.write(quote_string(text))
			else:
				self.buf.write(text)
			self.offset += len(text)
		if klass:
			if self.html:
				self.buf.write("</span>")
			elif self.color:
				self.buf.write(term_color())

	def wrote_space(self):
		return self.buf.getvalue()[-1].isspace()

	def text(self):
		return self.buf.getvalue()

def html_format(node):
	fmt = Formatter(pretty=False)
	fmt.format(node)
	return fmt.text()

def xml(node):
	fmt = Formatter(html=False, pretty=False, strip_comments=False)
	fmt.format(node)
	return fmt.text()

def print_node(root):
	for node in root:
		loc = node.location
		print(loc.start, loc.end, node.type, node.tree.source[start:end])
		if node.type == "tag":
			print_node(node)

if __name__ == "__main__":
	if len(sys.argv) <= 1:
		exit()
	try:
		tree = parse(sys.argv[1])
		fmt = Formatter(pretty=False, html=False, color=True)
		fmt.format(tree)
		sys.stdout.write(fmt.text())
	except (BrokenPipeError, KeyboardInterrupt):
		pass
	except Error as err:
		print(err, file=sys.stderr)
