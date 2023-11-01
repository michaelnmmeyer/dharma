# We could use lxml.etree, xml.etree, or bs4. We don't because we want to track
# accurate file locations (line + column). An annoyance of bs4 is that it tries
# to fix invalid files, this is great for some use cases but we don't want
# that. Using our code is also convenient for adding extra attributes or
# methods to nodes.

# TODO add a node set at the root of the tree to check that we don't attempt to
# insert the same node at several locations; or maybe just duplicate the node
# automatically if we see it's a duplicate. yes, solution 2 is best

import os, re, io, collections, copy, sys
from xml.parsers import expat
from xml.sax.handler import ContentHandler, ErrorHandler
from xml.sax.saxutils import escape as quote_string
from xml.sax.xmlreader import XMLReader
from xml.sax.expatreader import create_parser
from xml.etree import ElementTree

try:
	from xml.sax.handler import LexicalHandler
except ImportError:
	# Older python < 3.11
	class LexicalHandler:
		startCDATA = None
		endCDATA = None
		startDTD = None
		endDTD = None

__all__ = ["Error", "parse"]

attribute_tbl = str.maketrans({
	'"': "&quot;",
	"<": "&lt;",
	">": "&gt;",
	"&": "&amp;",
})

# We don't use xml.sax.saxutils.quoteattr because it tries to use ' as
# delimitor.
def quote_attribute(s):
	return s.translate(attribute_tbl)

class Error(Exception):

	def __init__(self, node, message):
		self.node = node
		self.message = message

	def __str__(self):
		"""
		path, (start, end) = self.node.tree.path, self.node.location
		problem = ["%s: offset %s: %s" % (path, start, self.message)]
		src = self.node.tree.source.splitlines()[line - 1]
		problem.append(src)
		cursor = (column - 1) * " " + "^ here"
		problem.append(cursor)
		return "\n".join(problem)
		"""
		return self.message # XXX

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
	location = None # (start_offset, end_offset) in the source file
	parent = None

	def __hash__(self):
		return id(self)

	@property
	def source(self):
		if not self.location or not self.tree:
			return
		start, end = self.location
		return self.tree.source[start:end].decode()

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

	def __bool__(self):
		return True

	def __str__(self):
		return "<?%s %s?>" % (self.target, self.data)

	def __repr__(self):
		return str(self)

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
		return quote_string(str(self.data))

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

class Branch(Node, list):

	def __bool__(self):
		return True

	def __contains__(self, node):
		for child in self:
			if child is node:
				return True
		return False

	# merge adjacent string nodes
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
			if name == ".":
				pass
			elif name == "..":
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
		for k, v in sorted(self.attrs.items()):
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

	def bad(self, msg):
		self.problems.append(msg)
		if self.tree:
			self.tree.bad_nodes.add(self)

	@property
	def path(self):
		buf = []
		node = self
		while True:
			buf.append(node.name)
			node = node.parent
			if not node:
				break
		buf.reverse()
		return "/" + "/".join(buf)

	def __getitem__(self, key):
		if isinstance(key, int):
			return list.__getitem__(self, key)
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
		if key == "lang":
			if isinstance(value, str):
				value = value.rsplit("-", 1)
			assert isinstance(value, list) or isinstance(value, tuple)
			assert 1 <= len(value) <= 2
			value = value[0]
		# always normalize space # XXX do that on the xml not on str(xml)
		self.attrs[key] = " ".join(str(value).strip().split())

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
		# for now, don't sort attrs for normalization
		for k, v in self.attrs.items():
			if isinstance(v, tuple):
				v = "-".join(v)
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
	# XML source, in bytes, encoded as UTF-8
	source = None

	def __init__(self):
		self.tree = self
		self.bad_nodes = set()

	def __repr__(self):
		if self.path:
			return "<Tree path=%r>" % self.path
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

	def __init__(self, source, path=None, keep_namespaces=False):
		self.keep_namespaces = keep_namespaces
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
		if isinstance(source, str):
			source = source.encode()
		if source.startswith(b'\xef\xbb\xbf'):
			source = source[3:]
		self.tree.source = source
		self.tree.path = path
		self.tree.location = (1, 0)
		self.last_node = None

	def parse(self):
		self.parser.Parse(self.tree.source, True)
		if self.last_node:
			last_start, _ = self.last_node.location
			self.last_node.location = (last_start, len(self.tree.source))
		return self.tree

	def set_location(self, node, close=False):
		start = self.parser.CurrentByteIndex
		if self.last_node is not None:
			last_start, _ = self.last_node.location
			self.last_node.location = (last_start, start)
		if not close:
			node.location = (start, None)
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
		assert self.parser.CurrentByteIndex == 0
		# should we save this?

	def StartDoctypeDeclHandler(self, doctypeName, systemId, publicId, has_internal_subset):
		raise Exception

	def EndDoctypeDeclHandler(self):
		raise Exception

	def ElementDeclHandler(self, name, model):
		raise Exception

	def AttlistDeclHandler(self, elname, attname, type, default, required):
		raise Exception

	def StartElementHandler(self, name, attributes):
		attrs = []
		if not self.keep_namespaces:
			colon = name.find(":")
			if colon >= 0:
				name = name[colon + 1:]
		for i in range(0, len(attributes), 2):
			key, value = attributes[i:i + 2]
			if not self.keep_namespaces:
				colon = key.find(":")
				if colon >= 0:
					key = key[colon + 1:]
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
		if len(parent) > 0 and parent[-1].type == "string":
			# need to save the location because we set it to None
			# when the string is modified
			loc = parent[-1].location
			parent[-1].append(data)
			parent[-1].location = loc
		else:
			self.make_node(String, data)

	def EntityDeclHandler(self, entityName, is_parameter_entity, value, base, systemId, publicId, notationName):
		raise Exception

	def NotationDeclHandler(self, notationName, base, systemId, publicId):
		raise Exception

	def StartNamespaceDeclHandler(self, prefix, uri):
		raise Exception

	def EndNamespaceDeclHandler(self, prefix):
		raise Exception

	def CommentHandler(self, data):
		self.make_node(Comment, data)

	def StartCdataSectionHandler(self):
		raise Exception

	def EndCdataSectionHandler(self):
		raise Exception

	def DefaultHandler(self, data):
		if data.strip():
			raise Exception
		self.CharacterDataHandler(data)

	def NotStandaloneHandler(self):
		raise Exception

	def ExternalEntityRefHandler(self, context, base, systemId, publicId):
		raise Exception

def parse_string(source, **kwargs):
	return Parser(source, **kwargs).parse()

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

class Formatter:

	indent_string = 2 * " "
	max_width = 80 ** 10 # soft, not hard

	def __init__(self, html=True, pretty=True, strip_comments=True, color=False):
		self.indent = 0
		self.offset = 0
		self.buf = io.StringIO()
		self.html = html
		self.pretty = pretty
		self.strip_comments = strip_comments
		self.color = color

	def format(self, node):
		if node.type == "tree":
			return self.format_tree(node)
		elif node.type == "tag":
			return self.format_tag(node)
		elif node.type == "string":
			return self.format_string(node)
		elif node.type == "comment":
			return self.format_comment(node)
		elif node.type == "instruction":
			return self.format_instruction(node)
		else:
			assert 0

	def format_tree(self, node):
		self.write('<?xml version="1.0" encoding="UTF-8"?>', klass="instruction")
		self.write("\n")
		for child in node:
			self.format(child)

	def format_instruction(self, node):
		self.write("<?%s %s?>" % (node.target, node.data), klass="instruction")
		if self.pretty:
			self.write("\n")

	def format_comment(self, node):
		node = node.data
		if self.strip_comments:
			return
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

	def format_tag(self, node):
		self.write("<", klass="tag")
		self.write("%s" % node.name, klass="tag")
		attrs = node.attrs.items()
		if self.pretty:
			attrs = sorted(attrs)
		for k, v in attrs:
			if k in ("lang", "space", "base", "id"):
				k = f"xml:{k}" # HACK
			if isinstance(v, tuple):
				v = "-".join(v)
			self.write(" ")
			self.write("%s" % k, klass="attr-name")
			self.write("=")
			self.write('"%s"' % quote_attribute(v), klass="attr-value")
		if len(node) == 0:
			self.write("/>", klass="tag")
		else:
			self.write(">", klass="tag")
			brk = False
			if self.pretty:
				if node[0].type == "string" and len(node[0].data) > 0 and node[0].data[0].isspace():
					self.write("\n")
					brk = True
				if brk:
					self.indent += 1
				for child in node:
					self.format(child)
				if brk:
					self.indent -= 1
			else:
				for child in node:
					self.format(child)
			self.write("</", klass="tag")
			self.write("%s" % node.name, klass="tag")
			self.write(">", klass="tag")
		if not self.pretty:
			return
		if node.parent:
			i = node.parent.index(node) + 1
			if i >= len(node.parent):
				return
			next = node.parent[i]
			if next.type != "string" or len(next.data) < 1 or not next.data[0].isspace():
				return
		self.write("\n")

	def write(self, text, klass=None):
		if klass:
			if self.html:
				self.buf.write('<span class="dh-%s">' % klass)
			elif self.color:
				self.buf.write(term_color(colors[klass]))
		if self.pretty:
			assert text == "\n" or not "\n" in text
			if text == "\n":
				self.buf.write("\n")
				self.offset = 0
			else:
				if self.offset == 0:
					self.buf.write(self.indent_string * max(0, self.indent))
					self.offset += len(self.indent_string) * max(0, self.indent)
				if self.html:
					self.buf.write(quote_string(text))
				else:
					self.buf.write(text)
				self.offset += len(text)
		else:
			if self.html:
				text = quote_string(text)
			self.buf.write(text)
		if klass:
			if self.html:
				self.buf.write("</span>")
			elif self.color:
				self.buf.write(term_color())

	def text(self):
		return self.buf.getvalue()

def html_format(node):
	fmt = Formatter(pretty=False)
	fmt.format(node)
	return fmt.text()

def pretty(node):
	fmt = Formatter(html=False)
	fmt.format_tag(node)
	return fmt.text()

def xml(node):
	fmt = Formatter(html=False, pretty=False, strip_comments=False)
	fmt.format(node)
	return fmt.text()

def print_node(root):
	for node in root:
		start, end = node.location
		print(start, end, node.type, node.tree.source[start:end])
		if node.type == "tag":
			print_node(node)

if __name__ == "__main__":
	if len(sys.argv) <= 1:
		exit()
	try:
		tree = parse(sys.argv[1])
		fmt = Formatter(pretty=True, html=False, color=True)
		fmt.format(tree)
		sys.stdout.write(fmt.text())
	except (BrokenPipeError, KeyboardInterrupt):
		pass
	except Error as err:
		print(err, file=sys.stderr)
