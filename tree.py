'''XML tree representation

Node types are: `Tree`, `Tag`, `Comment`, `String`, `Instruction`. Attributes
are not represented as nodes, because I don't really see the point. All node
types derive from an abstract base class `Node`. There is no inheritance
relationship between the different kinds of nodes: `Comment` is not a subclass
of `String` (unlike in bs4), etc. Thus, to check whether a node is of a given
type, using `isinstance(node, Comment)`, etc. is sufficient.

When parsing documents, we always normalize spaces in attributes: we replace
all sequences of whitespace characters with " " and we trim whitespace
from both sides.

For simplicity, we do not deal with XML namespaces at all. We just remove
namespace prefixes in both elements and attributes. Thus, `<xsl:template>`
becomes `<template>`, and `<foo xml:lang="eng">` becomes `<foo lang="eng">`.
This means that we cannot deal with documents where namespaces are significant.
This also means that we cannot serialize properly XML documents that used
namespaces initially.
'''

import os, re, io, collections, copy, sys
from xml.parsers import expat
from xml.sax.saxutils import escape as quote_string

DEFAULT_LANG = "eng"
DEFAULT_SPACE = "default"

Location = collections.namedtuple("Location", "start end line column")
'''Represents the location of a node in an XML file.'''

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

def unique(items):
	ret = []
	for item in items:
		if not item in ret:
			ret.append(item)
	return ret

def parse_string(source, **kwargs):
	'''Parse a string into a tree.'''
	#  We always pass byte strings to the parser because expat only
	# reports byte offsets, not code points offsets.
	if isinstance(source, str):
		source = source.encode()
	try:
		return Parser(source, **kwargs).parse()
	except expat.ExpatError as e:
		err = e
	# https://docs.python.org/3/library/pyexpat.html#xml.parsers.expat.XMLParserType
	# err.offset counts columns from 0
	raise Error(path=kwargs.get("path", "<memory>"),
		line=err.lineno, column=err.offset + 1,
		text=expat.errors.messages[err.code], source=source)

def parse(file, **kwargs):
	'''File can be either a file-like object or a string.'''
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

class Node(object):

	@property
	def tree(self):
		'''The `Tree` this node belongs to. If the node is a `Tree`,
		this returns the `Tree` itself.'''
		node = self
		while not isinstance(node, Tree):
			node = node.parent
		return node

	@property
	def file(self):
		"Path of the XML file this subtree was constructed from."
		return self.tree.file

	location = None
	'''`Location` object, which indicates the boundaries of the subtree in the
	XML source it was constructed from. If the subtree does not come from an
	XML file, `Location` is `None`. Likewise, if the subtree is modified in
	some way, or if it is extracted from the original tree or copied from it,
	`Location` will be set to `None`.'''

	_parent = None

	@property
	def parent(self):
		'''Parent node. All nodes have a parent, except `Tree` nodes,
		whose parent is `None`.'''
		ret = self._parent
		if ret is None:
			ret = Tree()
			self._parent = ret
			list.append(ret, self)
		return ret

	@property
	def path(self):
		"The path of this node. See the `locate` method."
		raise NotImplementedError

	type = None
	'''A string describing the node type: one of "tree", "tag", "string",
	"comment", "instruction".'''

	def __hash__(self):
		return id(self)

	def __bool__(self):
		return True

	@property
	def source(self):
		'''XML source of this subtree, as it appears in the file it
		was parsed from, as a string. If the `location` member is
		`None`, `source` will also be `None`.
		'''
		return self.byte_source.decode()

	@property
	def byte_source(self):
		"XML source of this subtree, in bytes, encoded as UTF-8."
		if not self.location:
			return
		return self.tree.byte_source[self.location.start:self.location.end]

	@property
	def root(self):
		'''The root `Tag` node of the `Tree` this subtree belongs to.
		'''
		return self.tree.root

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
		"""Removes this node and all its descendants from the tree.
		Returns the removed subtree."""
		parent = self._parent
		if parent:
			return parent.remove(self)
		self._parent = None
		self.location = None
		return self

	_location_re = re.compile(r"/(\w+)\[([1-9][0-9]*)\]", re.ASCII)

	def locate(self, path):
		'''Finds the node that matches the given xpath expression.
		This only works for basic expressions of the form:
		`/`, `/foo[1]`, `/foo[1]/bar[5]`, etc. The path of a Node
		is given in its path attribute.
		'''
		orig = path
		node = self.tree
		if path == "/":
			return node
		while True:
			match = self._location_re.match(path)
			if not match:
				raise Exception(f"invalid location {repr(orig)}")
			name, index = match.group(1), int(match.group(2))
			i = 0
			for node in node:
				if isinstance(node, Tag) and node.name == name:
					i += 1
					if i == index:
						break
			else:
				raise Exception(f"node {repr(orig)} not found")
			end = match.end()
			if end == len(path):
				break
			path = path[end:]
		return node

	def replace_with(self, other):
		'''Removes this node and its descendants from the tree, and
		puts another node in its place. Returns the removed subtree.
		'''
		parent = self.parent
		i = parent.index(self)
		del parent[i]
		parent.insert(i, other)
		return self

	def text(self, space="default"):
		'''Returns the text contents of this subtree. Per default, we do
		normalize-space(); to prevent this, pass `space="preserve"`.
		'''
		return ""

	def xml(self, space="default", strip_comments=False):
		'''Returns an XML representation of this subtree, typically not
		identical to the original XML source, if any.'''
		raise NotImplementedError

	def __copy__(self):
		return self.copy()

	def __deepcopy__(self, memo):
		return self.copy()

	def copy(self):
		'''Makes a copy of this subtree. The returned object holds no
		reference to the original.'''
		raise NotImplementedError

	def unwrap(self):
		'''Removes a node from the tree but leaves its descendants
		in-place. Cannot be called on a `Tree` node. Note that
		unwrapping the root `Tag` node of a `Tree` might yield
		an invalid XML document that contains several roots.'''
		self.delete()

	def coalesce(self):
		'''Coalesces adjacent string nodes and removes empty string
		nodes from this subtree. Has no effect on nodes other than
		`Tree` and `Tag`. In particular, if this is called on an
		empty `String` node, this node will not be removed from the
		tree.'''
		pass

class String(Node, collections.UserString):
	""

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

	def copy(self):
		return String(self.data)

class Comment(Node, collections.UserString):
	""

	type = "comment"

	def __repr__(self):
		return self.xml()

	def __str__(self):
		return self.xml()

	def xml(self, **kwargs):
		if kwargs.get("strip_comments"):
			return ""
		return f"<!--{self.data}-->"

	def text(self, **kwargs):
		return ""

	def copy(self):
		return Comment(self.data)

class Instruction(Node):
	"Represents a processing instruction."

	type = "instruction"

	def __init__(self, target, data):
		self.target = target
		self.data = data

	def __str__(self):
		return "<?%s %s?>" % (self.target, self.data)

	def __repr__(self):
		return str(self)

	def xml(self, **kwargs):
		return "<?%s %s?>" % (self.target, self.data)

	def copy(self):
		return Instruction(self.target, self.data)

class Branch(Node, list):
	# Non-leaf nodes viz. `Tree` nodes and `Tag` nodes.

	# Note that we check for objects identity: we compare pointers instead
	# of using __eq__.
	def __contains__(self, node):
		for child in self:
			if child is node:
				return True
		return False

	def coalesce(self):
		i = 0
		while i < len(self):
			cur = self[i]
			if isinstance(cur, String):
				if not cur.data:
					del self[i]
				elif i < len(self) - 1 and isinstance(self[i + 1], String):
					cur.append(self[i + 1])
					del self[i + 1]
			elif isinstance(cur, Tag):
				cur.coalesce()
				i += 1
			else:
				i += 1

	# Note that we check for objects identity: we compare pointers instead
	# of using __eq__.
	def index(self, node):
		for i, child in enumerate(self):
			if child is node:
				return i
		raise ValueError("not found")

	# Remove the given child node
	def remove(self, node):
		i = self.index(node)
		del self[i]

	def clear(self):
		while len(self) > 0:
			del self[0]

	def __setitem__(self, key, value):
		assert isinstance(key, int)
		self[key].replace_with(value)

	def __delitem__(self, i):
		node = self[i]
		node._parent = None
		node.location = None
		list.__delitem__(self, i)

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
			else:
				roots = [node for root in roots for node in root.children(name, index)]
			path = path[end + 1:]
		return roots

	def first(self, path):
		ret = self.find(path)
		if ret:
			return ret[0]

	def insert(self, i, node):
		if isinstance(node, Node):
			assert not isinstance(node, Tree)
			# Detach the node from the tree it belongs to, if any.
			# The node might already belong to this tree.
			node.delete()
		else:
			assert isinstance(node, str), "%r" % node
			node = String(node)
		if i < 0:
			i += len(self)
			if i < 0:
				i = 0
		elif i > len(self):
			i = len(self)
		node._parent = self
		list.insert(self, i, node)

	def append(self, node):
		self.insert(len(self), node)

	def prepend(self, node):
		self.insert(0, node)

class Tree(Branch):
	'''`Tree` represents the XML document proper. It must contain a single
	tag node and optionally comments and processing instructions. `Tree`
	objects constructed from files also hold blank `String` nodes for
	new lines, etc.
	'''

	type = "tree"
	path = "/"

	_byte_source = None

	location = None

	def __init__(self):
		pass

	parent = None

	_file = None

	@property
	def file(self):
		return self._file

	@property
	def root(self):
		for node in self:
			if isinstance(node, Tag):
				return node
		raise Exception("attempt to retrieve the root tag of a tree that does not have one")

	@property
	def byte_source(self):
		return self._byte_source

	def __repr__(self):
		if self.file:
			return f"<Tree file={self.file!r}>"
		return "<Tree>"

	def xml(self, **kwargs):
		ret = []
		for node in self:
			ret.append(node.xml(**kwargs))
		return "".join(ret)

	def text(self, **kwargs):
		if self.root:
			return self.root.text(**kwargs)

	def delete(self):
		raise Exception("nodes of type 'tree' cannot be deleted")

	def insert(self, i, node):
		if isinstance(node, Tag):
			if self.root:
				raise Exception("cannot add a root tag to a tree that already has one")
		super().insert(i, node)

	def copy(self):
		ret = Tree()
		for node in self:
			ret.append(node.copy())
		return ret

	def replace_with(self, other):
		raise Exception("cannot replace Tree nodes")

	next = None
	prev = None

class Tag(Branch):

	type = "tag"
	attrs = None

	def __init__(self, name, *attributes_iter, **attributes):
		'''The argument `name` is the name of the node as a string, e.g.
		"html". The positional argument `*attributes_iter` is optional.
		If given, it must be a single iterator that returns tuples
		of the form `(key, value)`, or a `dict` subclass. Attributes
		can also be passed as keyword arguments with `**attributes`.

		Attributes ordering is preserved for attributes passed through
		`*attributes_iter`. This is the reason we have it. New
		attributes created manually with e.g. `node["attr"] = "foo"`
		are added at the end of the attributes list (we use an
		OrderedDict under the hood).
		'''
		self.name = name
		self.attrs = collections.OrderedDict()
		self.problems = []
		if attributes_iter:
			assert len(attributes_iter) == 1
			attrs = attributes_iter[0]
			if isinstance(attrs, dict):
				attrs = attrs.items()
			for key, value in attrs:
				self[key] = value
		for key, value in attributes.items():
			self[key] = value

	def __hash__(self):
		return id(self)

	def __delitem__(self, i):
		node = self[i]
		node.location = None
		stack = [node]
		while stack:
			root = stack.pop()
			for child in root:
				child.location = None
				if isinstance(child, Tag):
					stack.append(child)
		super().__delitem__(i)

	def copy(self):
		ret = Tag(self.name, self.attrs)
		for child in self:
			ret.append(child.copy())
		return ret

	def __repr__(self):
		ret = "<%s" % self.name
		for k, v in self.attrs.items():
			ret += ' %s=%s' % (k, quote_attribute(v))
		ret += ">"
		return ret

	def __contains__(self, val):
		if isinstance(val, Node):
			return super().__contains__(val)
		assert isinstance(val, str)
		return val in self.attrs

	def unwrap(self):
		parent = self.parent
		i = parent.index(self)
		list.__delitem__(parent, i)
		for p, node in enumerate(self, i):
			node._parent = parent
			list.insert(parent, p, node)
		self._parent = None
		self.location = None
		list.clear(self)
		return self

	def bad(self, msg):
		self.problems.append(msg)

	@property
	def path(self):
		buf = []
		node = self
		while not isinstance(node, Tree):
			parent = node.parent
			index = 0
			for child in parent:
				if not isinstance(child, Tag):
					continue
				if child.name == node.name:
					index += 1
					if child is node:
						break
			assert index > 0
			buf.append(f"/{node.name}[{index}]")
			node = parent
		assert buf
		buf.reverse()
		return "".join(buf)

	def __getitem__(self, key):
		if isinstance(key, int):
			return super().__getitem__(key)
		assert isinstance(key, str)
		return self.attrs.get(key, "")

	def __setitem__(self, key, value):
		if isinstance(key, int):
			super().__setitem__(key, value)
		else:
			assert isinstance(key, str)
			assert isinstance(value, str)
			# Always normalize space.
			value = " ".join(value.strip().split())
			self.attrs[key] = value

	def __delitem__(self, key):
		if isinstance(key, int):
			super().__delitem__(key)
		else:
			assert isinstance(key, str)
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
		self.tree._byte_source = source
		self.tree._file = path
		self.tree.location = Location(0, len(source), 1, 1)
		self.last_node = None

	def parse(self):
		self.parser.Parse(self.tree.byte_source, True)
		if self.last_node:
			loc = self.last_node.location
			self.last_node.location = Location(loc.start, len(self.tree.byte_source), loc.line, loc.column)
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
		parent = self.stack[-1]
		node._parent = parent
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
			data += " standalone=" + quote_attribute(
				standalone and "yes" or "no")
		self.make_node(Instruction, "xml", data[1:])

	def StartDoctypeDeclHandler(self, doctypeName, systemId, publicId,
		has_internal_subset):
		raise NotImplementedError

	def EndDoctypeDeclHandler(self):
		raise NotImplementedError

	def ElementDeclHandler(self, name, model):
		raise NotImplementedError

	def AttlistDeclHandler(self, elname, attname, type, default, required):
		raise NotImplementedError

	def StartElementHandler(self, name, attributes):
		# Drop all namespaces, in the tag name and in attributes.
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
		self.set_location(node, close=True)

	def ProcessingInstructionHandler(self, target, data):
		self.make_node(Instruction, target, data or "")

	def CharacterDataHandler(self, data):
		assert len(data) > 0
		parent = self.stack[-1]
		if len(parent) > 0 and isinstance(parent[-1], String):
			# Need to save and restore the location because we set
			# it to None when the string is modified
			loc = parent[-1].location
			parent[-1].append(data)
			parent[-1].location = loc
		else:
			self.make_node(String, data)

	def EntityDeclHandler(self, entityName, is_parameter_entity, value,
		base, systemId, publicId, notationName):
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

class Error(Exception):
	"Raised for parsing errors."

	def __init__(self, line=0, column=0, text="", source=b"", path=""):
		self.path = path
		self.line = line
		self.column = column
		self.text = text
		self.source = source

	def __str__(self):
		return f"Error(path='{self.path}' line={self.line}, column={self.column}, text={repr(self.text)})"

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
