'''XML tree representation.

Node types are: `Tree`, `Tag`, `Comment`, `String`, `Instruction`. Attributes
are not represented as nodes, even though they are treated like that in the
xpath model, because this would be weird in python.

All node types derive from an abstract base class `Node`. `Tree` and `Tag` nodes
derive from a `Branch` abstract class, which itself derives from `Node`. There
is no inheritance relationship between concrete node types. For instance,
`Comment` is not a subclass of `String`, unlike in bs4. Thus, to check whether a
node is of a concrete given type `T`, using `isinstance(node, T)`, etc. is
sufficient. And to check whether a node is a branch or a leaf, it is sufficient
to check `isinstance(node, Branch)`.

When parsing documents and when modifying attributes, we always normalize spaces
in attributes: we replace all sequences of whitespace characters with " " and we
trim whitespace from both sides.

For simplicity, we do not deal with XML namespaces at all. We just remove
namespace prefixes in both elements and attributes. Thus,
`<xsl:template>` becomes `<template>`, and `<foo xml:lang="eng">` becomes `<foo
lang="eng">`. This means that we cannot deal with documents where namespaces are
significant. This also means that we cannot serialize properly XML documents
that used namespaces initially.

We only support a small subset of xpath. Most notably, it is only possible to
select tag nodes and the XML tree itself. Other types of nodes, e.g. attributes,
can only be used as predicates, as in `foo[@bar]`. We also do not support
expressions that index node sets in some way: testing a node position in a node
set is not possible.

To evaluate an expression, we first convert it to straightforward python source
code, then compile the result, and finally run the code. Compiled expressions
are saved in a global table and are systematically reused. No caching policy for
now.
'''

import os, re, io, collections, copy, sys, inspect, fnmatch, argparse, tokenize
import traceback
from xml.parsers import expat
from xml.sax.saxutils import escape as quote_string
from pegen.tokenizer import Tokenizer
from dharma.xpath_parser import Path, Step, Op, Func, GeneratedParser

DEFAULT_LANG = "eng"
DEFAULT_SPACE = "default"

Location = collections.namedtuple("Location", "start end line column")
'''Represents the location of a node in an XML file. Fields are:

* `start`: byte index of the start of the node
* `end`: idem for the end of the node
* `line`: line number (one-based)
* `column`: column number (one-based)
'''

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

def parse_string(source, path=None):
	'''Parse an XML string into a `Tree`. If `path` is given, it will be
	used as filename in error messages, and will be accessible through
	the `file` attribute.'''
	#  We always pass byte strings to the parser because expat only
	# reports byte offsets, not code points offsets, so, to report
	# errors locations properly, we need a byte string.
	if isinstance(source, str):
		source = source.encode()
	try:
		return Parser(source, path=path).parse()
	except expat.ExpatError as e:
		err = e
	# https://docs.python.org/3/library/pyexpat.html#xml.parsers.expat.XMLParserType
	# err.offset counts columns from 0
	raise Error(path=path or "<memory>",
		line=err.lineno, column=err.offset + 1,
		text=expat.errors.messages[err.code], source=source)

def parse(file, path=None):
	'''Parse an XML file into a `Tree`. The `file` argument can either be a
	file-like object or a string that indicates the file's path. The `path`
	argument can be used to indicate the file's path, for errors messages.
	If it is not given, the path of the file will be deduced from `file`,
	if possible.'''
	if hasattr(file, "read"):
		# assume file-like
		source = file.read()
		if not path and file is not sys.stdin and hasattr(file, "name"):
			path = os.path.abspath(str(file.name))
	else:
		with open(file, "rb") as f:
			source = f.read()
		if not path:
			path = os.path.abspath(file)
	return parse_string(source, path=path)

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
		# Newly created nodes are not immediately attached to a tree.
		# It is only if an attempt is made to access a node's tree
		# that a new tree is allocated. We do this to avoid creating
		# new tree objects for each new node, when in practice most
		# nodes will be immediately appended to an existing tree.
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
		`/`, `/foo[1]`, `/foo[1]/bar[5]`, etc. The path of a node
		is given in its `path` attribute.
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

	def find(self, path):
		'''Finds nodes that match the given XPath expression. Returns a
		list of matching nodes.
		'''
		f = generator.compile(path)
		return list(f(self))

	def first(self, path):
		'''Like the `find` method, but returns only the first matching
		node, or `None` if there is no match.'''
		f = generator.compile(path)
		return next(f(self), None)

	@staticmethod
	def match_func(path):
		'''Returns a function that matches the given path if called on
		a node.'''
		return generator.compile(path, search=False)

	def matches(self, path):
		'''Checks if this node matches the given XPath expression.'''
		f = self.match_func(path)
		return f(self)

	def children(self):
		'''Returns a list of `Tag` children of this node.'''
		return []

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

	def xml(self, pretty=False, strip_comments=False,
		strip_instructions=False, html=False, color=False):
		'''Returns an XML representation of this subtree.

		If `html` is true, the result will be escaped, for inclusion
		in an HTML file. If `color` is true, the result will be
		colorized, either through CSS classes (if `html` is true),
		or with ANSI escapes codes (otherwise).
		'''
		fmt = Formatter(pretty=pretty, strip_comments=strip_comments,
			strip_instructions=strip_instructions, html=html,
			color=color)
		fmt.format(self)
		return fmt.text()

	def __copy__(self):
		return self.copy()

	def __deepcopy__(self, memo):
		return self.copy()

	def copy(self):
		'''Makes a copy of this subtree. The returned object holds no
		reference to the original. It is bound to a new `Tree`.'''
		raise NotImplementedError

	def unwrap(self):
		'''Removes a node from the tree but leaves its descendants
		in-place. Returns the detached node.

		This cannot be called on a `Tree` node. Also note that
		unwrapping the root `Tag` node of a `Tree` might yield
		an invalid XML document that contains several roots.'''
		self.delete()
		return self

	def coalesce(self):
		'''Coalesces adjacent string nodes and removes empty string
		nodes from this subtree. Has no effect on leaf nodes. In
		particular, if this is  called on an empty `String` node, this
		node will not be removed from the tree.'''
		pass

class Branch(Node, list):
	'''Base class for non-leaf nodes viz. `Tree` nodes and `Tag` nodes.

	Branches are represented as lists of nodes. They support most `list`
	operations. Those that are not implemented will raise an exception if
	called.
	'''

	def __add__(self, value):
		ret = self.copy()
		ret.extend(value.copy())
		return ret

	def __eq__(self, value):
		raise NotImplementedError

	def __ge__(self, value):
		raise NotImplementedError

	def __gt__(self, value):
		raise NotImplementedError

	def __iadd__(self, value):
		self.extend(value)

	def __imul__(self, value):
		raise NotImplementedError

	def __le__(self, value):
		raise NotImplementedError

	def __lt__(self, value):
		raise NotImplementedError

	def __mul__(self, value):
		raise NotImplementedError

	def __ne__(self, value):
		raise NotImplementedError

	def __rmul__(self, value):
		raise NotImplementedError

	def count(self, value):
		raise NotImplementedError

	def pop(self, index=-1):
		node = self[index]
		del self[index]
		return node

	def extend(self, iterable):
		for node in iterable:
			self.append(node)

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

	# Note that we check for objects identity: we compare pointers instead
	# of using __eq__.
	def __contains__(self, node):
		for child in self:
			if child is node:
				return True
		return False

	def children(self):
		ret = []
		for node in self:
			if isinstance(node, Tag):
				ret.append(node)
		return ret

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

	def insert(self, i, node):
		if isinstance(node, Node):
			assert not isinstance(node, Tree)
			# Detach the node from the tree it belongs to, if any.
			# The node might already belong to this tree.
			node.delete()
		else:
			assert isinstance(node, str), repr(node)
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

	path = "/"

	_byte_source = None

	location = None

	def __init__(self):
		# Prevent initialization with an iterator, because in `Tag`
		# we do not allows this either.
		pass

	parent = None

	_file = None

	@property
	def file(self):
		return self._file

	@property
	def root(self):
		ret = None
		for node in self:
			if isinstance(node, Tag):
				if ret is not None:
					raise Exception("multiple root tags in XML document")
				ret = node
		if not ret:
			raise Exception("attempt to retrieve the root tag of a tree that does not have one")
		return ret

	@property
	def byte_source(self):
		return self._byte_source

	def __repr__(self):
		if self.file:
			return f"<Tree file={self.file!r}>"
		return "<Tree>"

	def text(self, **kwargs):
		if self.root:
			return self.root.text(**kwargs)

	def delete(self):
		raise Exception("nodes of type 'tree' cannot be deleted")

	def insert(self, index, node):
		if isinstance(node, Tag):
			if any(isinstance(child, Tag) for child in self):
				raise Exception("cannot add a root tag to a tree that already has one")
		elif isinstance(node, (String, str)):
			if not node.isspace():
				raise Exception("cannot add text contents to a Tree node")
		super().insert(index, node)

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
	'''Represents element nodes.

	`Tag` objects have both a `list`-like and a `dict`-like interface.

	When they are indexed with integers, the children of the node are
	accessed. When they are indexed with strings, XML attributes are
	accessed. Indexing an attribute that the `Tag` does not possess is
	not treated as an error, and returns the empty string.

	The `in` operator also takes types into account: if a `Node` is given,
	it will check whether this node is a child of `Tag`. Otherwise, it
	assumes the argument is an attribute name, and checks whether the
	`Tag` bears this attribute.

	Iterating over a `Tag` node yields the tag's children. The methods
	`keys()`, `values()` and `items()` can be used for iterating over
	attributes.
	'''

	def __init__(self, name, *attributes_iter, **attributes):
		'''The argument `name` is the name of the node as a string, e.g.
		"html". This argument can be followed by a single positional
		argument `attributes_iter`. If given, it must be an
		iterator that returns tuples of the form `(key, value)`, or a
		`dict` subclass. Attributes can also be passed as keyword
		arguments with `**attributes`.

		Attributes ordering is preserved for attributes passed through
		`attributes_iter`. This is the reason we have it. New
		attributes created manually with e.g. `node["attr"] = "foo"`
		are added at the end of the attributes list. (We use an
		OrderedDict under the hood.)
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

	def keys(self):
		return self.attrs.keys()

	def values(self):
		return self.attrs.values()

	def items(self):
		return self.attrs.items()

	def __repr__(self):
		ret = f"<{self.name}"
		for k, v in self.attrs.items():
			ret += f' {k}={quote_attribute(v)}'
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
		if isinstance(key, str):
			return self.attrs.get(key, "")
		return super().__getitem__(key)

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

	def text(self, **kwargs):
		buf = []
		for node in self:
			buf.append(node.text(**kwargs))
		return "".join(buf)

class String(Node, collections.UserString):
	'''Represents a text node.

	`String` nodes behave like normal `str` objects, but they can also be
	edited in-place with the following methods.'''

	def clear(self):
		"Sets this `String` to the empty string."
		if self.data == "":
			return
		self.location = None
		self.data = ""

	def append(self, data):
		"Adds text at the end of this `String`."
		if not data:
			return
		self.location = None
		self.data += data

	def prepend(self, data):
		"Adds text at the beginning of this `String`."
		if not data:
			return
		self.location = None
		self.data = data + self.data

	def insert(self, index, data):
		"Adds text at the given index of this `String`."
		if not data:
			return
		self.location = None
		if index < 0:
			index += len(self.data)
			if index < 0:
				index = 0
		elif index > len(self.data):
			index = len(self.data)
		self.data = self.data[:index] + data + self.data[index:]

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
	'''Represents a comment.

	`Comment` nodes behave like strings.
	'''

	def __repr__(self):
		return self.xml()

	def __str__(self):
		return self.xml()

	def copy(self):
		return Comment(self.data)

class Instruction(Node):
	'''Represents a processing instruction.

	Initial XML declarations e.g. `<?xml version="1.0"?>` are also
	represented as processing instructions.
	'''

	def __init__(self, target, data):
		self.target = target
		self.data = data

	def __str__(self):
		return self.xml()

	def __repr__(self):
		return self.xml()

	def copy(self):
		return Instruction(self.target, self.data)

class Parser:

	def __init__(self, source, path=None):
		self.parser = expat.ParserCreate()
		self.parser.ordered_attributes = 1
		self.parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
		self.parser.buffer_text = True
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
			self.last_node.location = Location(loc.start,
				len(self.tree.byte_source),
				loc.line, loc.column)
		return self.tree

	def set_location(self, node, close=False):
		start = self.parser.CurrentByteIndex
		if self.last_node is not None:
			last = self.last_node.location
			self.last_node.location = Location(last.start, start,
				last.line, last.column)
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

	def StartDoctypeDeclHandler(self, doctypeName, systemId,
		publicId, has_internal_subset):
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

def xpath_glob(node, pattern, *arg):
	assert isinstance(pattern, str)
	(text,) = arg or (node.text(),)
	return fnmatch.fnmatchcase(text, pattern)

xpath_funcs = {
	"glob": xpath_glob,
}

def children(node):
	for child in node:
		if isinstance(child, Tag):
			yield child

def descendants(node):
	for child in node:
		if isinstance(child, Tag):
			yield child
			yield from descendants(child)

def descendants_or_self(node):
	yield node
	yield from descendants(node)

def ancestors(node):
	while True:
		node = node.parent
		if not node:
			break
		yield node

def ancestors_or_self(node):
	yield node
	yield from ancestors(node)

def following_siblings(node):
	if isinstance(node, Tag):
		parent = node.parent
		i = parent.index(node)
		for child in parent[i + 1:]:
			if isinstance(child, Tag):
				yield child

def preceding_siblings(node):
	if isinstance(node, Tag):
		parent = node.parent
		i = parent.index(node)
		for child in reversed(parent[:i]):
			if isinstance(child, Tag):
				yield child

def handle_token(buf, tok):
	match len(buf):
		case 0:
			match tok.type:
				case tokenize.NEWLINE:
					pass
				case tokenize.NAME:
					buf.append(tok)
				case _:
					yield tok
		case 1:
			match tok.type:
				case tokenize.NEWLINE:
					yield buf[0]
					buf.clear()
				case tokenize.OP if tok.string == "-" and buf[0].end == tok.start:
					buf.append(tok)
				case _:
					yield buf[0]
					buf.clear()
					yield tok
		case 2:
			match tok.type:
				case tokenize.NEWLINE:
					yield buf[0]
					yield buf[1]
					buf.clear()
				case tokenize.NAME if buf[1].end == tok.start:
					info = tokenize.TokenInfo(
						type=tokenize.NAME,
						string=buf[0].string + "-" + tok.string,
						start=buf[0].start, end=tok.end, line=buf[0].line)
					buf.clear()
					buf.append(info)
				case _:
					yield buf[0]
					yield buf[1]
					buf.clear()
					yield tok


# Like Python's tokenizer, but treats strings like "foo-bar-baz" as names.
def tokenize_xpath(s):
	buf = []
	for tok in tokenize.generate_tokens(io.StringIO(s).readline):
		yield from handle_token(buf, tok)

class Generator:

	def __init__(self):
		self.code = ""
		self.indents = []
		self.bufs = []
		self.routines_nr = 0
		self.env = {f.__name__: f
			for funcs in (xpath_funcs.values(), (Tag, Tree,
				children, descendants, descendants_or_self,
				ancestors, ancestors_or_self))
				for f in funcs}
		self.search = {}
		self.match = {}

	def parse(self, expr):
		gen = tokenize_xpath(expr)
		tokenizer = Tokenizer(gen, verbose=False)
		parser = GeneratedParser(tokenizer, verbose=False)
		root = parser.start()
		if not root:
			err = parser.make_syntax_error("<xpath expression>")
			traceback.print_exception(err.__class__, err, None)
			raise err
		return root

	def append(self, line):
		self.bufs[-1].append(self.indents[-1] * "\t" + line + "\n")
		if line.startswith("def ") or line.startswith("if ") \
			or line.startswith("for "):
			self.indents[-1] += 1

	def start_routine(self):
		buf = []
		self.indents.append(0)
		self.bufs.append(buf)
		self.routines_nr += 1
		return f"xpath_expression_{self.routines_nr}"

	def end_routine(self):
		code = self.bufs.pop()
		if self.bufs:
			code.append("\n")
		self.code += "".join(code)
		self.indents.pop()

	def compile(self, expr, search=True):
		if search:
			table, main_func = self.search, self.generate_main_search
		else:
			table, main_func = self.match, self.generate_main_match
		f = table.get(expr)
		if f:
			return f
		t = self.parse(expr)
		if os.getenv("DHARMA_DEBUG"):
			print(t, file=sys.stderr)
		assert isinstance(t, Path)
		main = main_func(t, expr)
		code = compile(self.code, "<xpath expression>", "exec")
		exec(code, self.env)
		f = self.env[main]
		setattr(f, "source_code", self.code)
		table[expr] = f
		self.code = ""
		self.indents.clear()
		self.bufs.clear()
		return f

	def generate(self, expr, code=None):
		match expr:
			case Path():
				name = self.start_routine()
				self.generate_path(expr, name)
				self.end_routine()
				return f"{name}(node)"
			case Step():
				self.generate_step(expr)
			case str():
				return expr
			case Op(val="or") | Op(val="and"):
				return f"bool({self.generate(expr.l)} {expr.val} {self.generate(expr.r)})"
			case Op(val="not"):
				return f"not {self.generate(expr.r)}"
			case Op():
				return f"{self.generate(expr.l)} {expr.val} {self.generate(expr.r)}"
			case Func():
				return self.generate_call(expr)
			case _:
				assert 0, "%r" % expr

	def generate_main_search(self, path, code):
		func_name = self.start_routine()
		self.append(f"def {func_name}(node):")
		self.append(repr(code))
		if path.absolute:
			self.append("node = node.tree")
		for step in path.steps:
			self.generate(step)
		self.append("yield node")
		self.end_routine()
		return func_name

	def generate_main_match(self, path, code):
		func_name = self.start_routine()
		self.append(f"def {func_name}(node):")
		self.append(repr(code))
		steps = list(reversed(path.steps))
		for i, step in enumerate(steps):
			if step.name_test:
				self.append(f"if isinstance(node, Tag) and node.name == {step.name_test!r}:")
			for pred in step.predicates:
				self.append(f"if {self.generate(pred)}:")
			if i == len(steps) - 1:
				if path.absolute and step.axis == "child":
					self.append("node = node.parent")
					self.append("if isinstance(node, Tree):")
				break
			match step.axis:
				case "self":
					pass
				case "child":
					self.append("node = node.parent")
					if not step.name_test:
						self.append("if node is not None:")
				case "descendant-or-self":
					self.append("for node in ancestors_or_self(node):")
				case _:
					assert 0, f"repr(step.axis) not allowed"
		self.append("return True")
		self.indents[-1] = 1
		self.append("return False")
		self.end_routine()
		return func_name

	def generate_path(self, path, func_name):
		self.append(f"def {func_name}(node):")
		if path.absolute:
			self.append("node = node.tree")
		for step in path.steps:
			self.generate(step)
		self.append("return True")
		self.indents[-1] = 1
		self.append("return False")

	def generate_step(self, step):
		match step.axis:
			case "self":
				pass
			case "child":
				self.append("for node in children(node):")
			case "descendant":
				self.append("for node in descendants(node):")
			case "descendant-or-self":
				self.append("for node in descendants_or_self(node):")
			case "parent":
				self.append("node = node.parent")
				self.append("if node is not None:")
			case "ancestor":
				self.append("for node in ancestors(node):")
			case "ancestor-or-self":
				self.append("for node in ancestors_or_self(node):")
			case "following-sibling":
				self.append("for node in following_siblings(node):")
			case "preceding-sibling":
				self.append("for node in preceding_siblings(node):")
			case _:
				assert 0, repr(step.axis)
		if step.name_test:
			self.append(f"if isinstance(node, Tag) and node.name == {step.name_test!r}:")
		for pred in step.predicates:
			self.append(f"if {self.generate(pred)}:")

	def generate_call(self, func):
		buf = []
		f = xpath_funcs.get(func.name)
		if not f:
			raise Exception(f"xpath function '{func.name}' not defined")
		buf.append(f"{f.__name__}(node, ")
		for i, arg in enumerate(func.args):
			buf.append(self.generate(arg))
			if i < len(func.args) - 1:
				buf.append(", ")
		buf.append(")")
		return "".join(buf)

generator = Generator()

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
		if isinstance(parent[i], String):
			if parent[i].rstrip() != parent[i]:
				return True
			if parent[i] != "":
				return False
		elif not isinstance(parent[i], (Comment, Instruction)):
			return False
		i -= 1
	return False

def space_after_opening(node):
	assert isinstance(node, Tag)
	i = 0
	while i < len(node):
		if isinstance(node[i], String):
			if node[i].lstrip() != node[i]:
				return True
			if node[i] != "":
				return False
		elif not isinstance(node[i], (Comment, Instruction)):
			return False
		i += 1
	return False

def space_before_closing(node):
	assert isinstance(node, Tag)
	i = len(node)
	while i > 0:
		i -= 1
		if isinstance(node[i], String):
			if node[i].rstrip() != node[i]:
				return True
			if node[i] != "":
				return False
		elif not isinstance(node[i], (Comment, Instruction)):
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
		strip_instructions=False, add_xml_prefix=False,
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
		self.strip_instructions = strip_instructions
		self.add_xml_prefix = add_xml_prefix

	def format_contents(self, node):
		for child in node:
			self.format(child)

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
		if self.strip_instructions:
			return
		self.write(f"<?{node.target} {node.data}?>", klass="instruction")
		if not self.pretty:
			return
		self.write("\n")

	def format_comment(self, node):
		if self.strip_comments:
			return
		node = node.data
		if not self.pretty:
			self.write(f"<!--{node}-->", klass="comment")
			return
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
			# follow people's habits.
			attrs = sorted(attrs)
		for k, v in attrs:
			if self.add_xml_prefix and k in ("lang", "space", "base", "id"):
				k = f"xml:{k}"
			self.write(" ")
			self.write(k, klass="attr-name")
			self.write("=")
			self.write(quote_attribute(v), klass="attr-value")
		if len(node) == 0:
			self.write("/>", klass="tag")
		else:
			self.write(">", klass="tag")

	def format_closing_tag(self, node):
		if len(node) == 0:
			return
		self.write("</", klass="tag")
		self.write(node.name, klass="tag")
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
				self.buf.write(f'<span class="{klass}">')
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

def html_format(node, skip_root=False, color=True, add_xml_prefix=True):
	fmt = Formatter(pretty=False, color=color, add_xml_prefix=add_xml_prefix)
	if skip_root:
		fmt.format_contents(node)
	else:
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
		exit(1)
	except Error as err:
		print(err, file=sys.stderr)
