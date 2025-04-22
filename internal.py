import re
from dharma import tree

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

def trim_before(node):
	parent = node.parent
	i = parent.index(node)
	if i > 0 and isinstance(parent[i - 1], tree.String) and parent[i - 1].endswith(" "):
		parent[i - 1].replace_with(parent[i - 1].data.rstrip())

def squeeze(strings):
	i = 0
	while i < len(strings):
		s = strings[i]
		if len(s) == 0:
			s.delete()
			del strings[i]
			continue
		ret = re.sub(r"\s+", " ", s.data)
		if ret[0] == " " and i > 0 and strings[i - 1].endswith(" "):
			ret = ret[1:]
		if ret != s.data:
			s.replace_with(tree.String(ret))
			strings[i] = ret
		i += 1

def traverse_milestones(root):
	match root:
		case tree.Tag() if root.name in ("npage", "nline", "ncell"):
			yield root
		case tree.Tag() | tree.Tree():
			for node in root:
				yield from traverse_milestones(node)

def complete_milestones(t):
	stack = []
	nodes = list(traverse_milestones(t))
	#XXX TODO
	return t







def impossible(node):
	if isinstance(node, tree.Branch):
		print("BAD", node.path, file=sys.stderr)
	else:
		print("BAD", node, file=sys.stderr)
	node.delete()

def full_squeeze(node):
	strings = node.strings()
	trim_left(strings)
	trim_right(strings)
	squeeze(strings)

def cleanup_inline(root):
	for node in list(root):
		match node:
			case tree.String():
				yield node
			case tree.Tag(name="span") | tree.Tag(name="link"):
				yield node

def cleanup_paras(root):
	for node in list(root):
		match node:
			case tree.Tag(name="para"):
				yield from cleanup_para(node)

def cleanup_para(root):
	for node in root:
		match node:
			case tree.Tag(name="list"):
				pass # TODO
			case tree.Tag(name="dlist"):
				pass # TODO
			case tree.Tag(name="quote"):
				pass # TODO
			case tree.String():
				pass
			case tree.Tag(name="span") | tree.Tag(name="link"):
				pass

def cleanup_division(root):
	itor = iter(list(root))
	for node in itor:
		match node:
			case tree.Tag(name="head"):
				yield from cleanup_inline(node)
				break
	for node in itor:
		if not isinstance(node, tree.Tag):
			continue
		match node.name:
			case "div":
				yield from cleanup_division(node)
			case "para" | "verse":
				yield from cleanup_para(node)
			case "npage" | "nline" | "ncell":
				pass # TODO

def cleanup_plain(root):
	for node in list(root):
		match node:
			case tree.String():
				yield node

def cleanup_person(node):
	pass

def cleanup_document(root):
	for node in root:
		if not isinstance(node, tree.Tag):
			continue
		match node.name:
			case "title":
				yield from cleanup_inline(node)
			case "author" | "editor":
				yield from cleanup_person(node)
			case "repository" | "identifier":
				yield from cleanup_plain(node)
			case "summary" | "hand":
				yield from cleanup_paras(node)
			case "edition" | "apparatus" | "translation" | \
				"commentary" | "bibliography":
				yield from cleanup_division(node)

def cleanup_tree(root):
	for node in root:
		match node:
			case tree.Tag(name="document"):
				yield from cleanup_document(node)
	return

	# TODO delete comments + processing instr
	for node in t.find("//div") + t.find("//verse"):
		for child in node:
			if not isinstance(child, tree.Tag):
				child.delete()
	for node in t.find("//note"):
		if node.empty:
			node.delete()
	for node in t.find("//para") + t.find("//head"):
		strings = node.strings()
		trim_left(strings)
		trim_right(strings)
		squeeze(strings)
		if node.empty:
			node.delete()
	for node in t.find("//*[name() = 'npage' or name() = 'nline' or name() = 'ncell']"):
		trim_before(node)
	if not t.empty:
		return t





def squeeze(s):
	return re.sub(r"\s+", " ", s)

def handle_string(buf, space, node):
	match space:
		case "add":
			text = squeeze(node.data.lstrip())
			if len(text) == 0:
				return "add"
			buf.append(" ")
			if text[-1].isspace():
				text = text[:-1]
				buf.append(text)
				return "add"
			buf.append(text)
			return "none"
		case "drop":
			text = squeeze(node.data.lstrip())
			if len(text) == 0:
				return "drop"
			if text[-1].isspace():
				text = text[:-1]
				buf.append(text)
				return "add"
			buf.append(text)
			return "none"
		case "none":
			text = squeeze(node.data.lstrip())
			if len(text) == 0:
				assert len(node) > 0
				return "add"
			if text[0].isspace():
				buf.append(" ")
				text = text[1:]
			if text[-1].isspace():
				text = text[:-1]
				buf.append(text)
				return "add"
			buf.append(text)
			return "none"

def handle_tag(buf, space, node):
	left_space, repl, right_space = handle_subtree(node)
	match space:
		case "add":
			match left_space:
				case "add" | "none":
					buf.append(" ")
		case "drop":
			if len(buf) > 0:
				match buf[-1]:
					case tree.String(data=" "):
						buf.pop()
		case "none":
			match left_space:
				case "add":
					buf.append(" ")
	if repl:
		buf.append(repl)
	match node.name:
		case "note":
			return "drop", space
		case "npage" | "nline" | "ncell":
			return "drop", "drop"
		case "span" | "link":
			return left_space, right_space
		case _:
			return "none", "none"

def handle_subtree(root):
	buf = tree.Tag(root.name, **root.attrs)
	space = "drop"
	if len(root) > 0:
		match (node := root[0]):
			case tree.String():
				left_space = space = handle_string(buf, space, node)
			case tree.Tag():
				left_space, space = handle_tag(buf, space, node)
		for node in root[1:]:
			match node:
				case tree.String():
					space = handle_string(buf, space, node)
				case tree.Tag():
					_, space = handle_tag(buf, space, node)
	return left_space, buf, space

def cleanup(doc: tree.Tree):
	# MUST be coalesced XXX add assertions
	return handle_subtree(doc.root)

"""
preprocessing for logical and full:
	complete pbs, etc.
	find a convention for the placement of pbs, etc. (beginning of node and end of previous node? within which container? etc.)

for physical:

traverse the tree in order, and make a stack of:
	npage
	nline
	ncell
we will have to allocate phantom pages/lines/cells, when a) the encoding is incorrect b) the encoding is correct but a category is missing. it is best to keep these phantom elements in the output than to remove them, for search.

except that if they occur within one of these, leave them as-is (viz. replace them with an inline annotation <1>, etc.).
	head
	note

we can't really tell whether numbering is continuous between textparts or not, so if we have:
	<pb n=X>foo<div type="textpart">bar<pb n=Z>
we assume that page X continues in the next textpart (instead of assuming that the next textpart is missing a <pb n=Y> at the very beginning). to represent the fact that page X continues in the next textpart, use a cont=true flag in the first div we generate within the next textpart.

when generating the search representation, not sure what to do with the textpart heading in the middle. might want to index separately the TOC (with all headings)
and the text (without interruption)

unwrap these elements:
	para
	verse
	verse-line
	list
	dlist

delete this one:
	verse-head

split these elements if needed:
	a
	para

keep as is:
	div


The resulting hierarchy must be:
	<page>
		<line>
			<cell>
				<link>
				<span>
"""

class PhysicalParser:

	def __init__(self, input):
		self.input = input
		self.stack = [tree.Tree()] # tree > page > line > cell

	def __call__(self):
		self.traverse(self.input)
		self.pop_stack(1)
		return self.stack[-1]

	def append(self, node):
		self.stack[-1].append(node.copy())

	def traverse(self, input):
		for node in input:
			match node:
				case tree.Tag():
					self.elem(node)
				case tree.String():
					self.append(node)

	def npage(self, node):
		while len(self.stack) >= 2:
			elem = self.stack.pop()
			self.stack[-1].append(elem)
		self.stack.append(tree.Tag("page", break_=node["break"]))

	def nline(self, node):
		if len(self.stack) < 2:
			self.stack.append(tree.Tag("page", break_="true"))
		while len(self.stack) >= 3:
			elem = self.stack.pop()
			self.stack[-1].append(elem)
		self.stack.append(tree.Tag("line", break_=node["break"]))

	def ncell(self, node):
		if len(self.stack) < 2:
			self.stack.append(tree.Tag("page", break_="true"))
		if len(self.stack) < 3:
			self.stack.append(tree.Tag("line", break_="true"))
		while len(self.stack) >= 4:
			elem = self.stack.pop()
			self.stack[-1].append(elem)
		self.stack.append(tree.Tag("cell", break_=node["break"]))

	def elem(self, node):
		match node.name:
			case "npage":
				self.npage(node)
			case "nline":
				self.nline(node)
			case "ncell":
				self.ncell(node)
			case "head" | "note":
				self.append(node)
			case "verse-head":
				pass
			case "para" | "verse" | "verse-line" | "list" | "dlist":
				self.traverse(node)
			case "link" | "span":
				pass
			case _:
				raise Exception("unexpected: {node!r}")

def to_physical(t):
	for node in t.find(".//span[@class='corr' and @standalone='false']"):
		node.delete()
	for node in t.find(".//span[@class='reg' and @standalone='false']"):
		node.delete()
	for node in t.find(".//ex"):
		node.delete()
	return t

def to_logical(t):
	for node in t.find(".//span[@class='sic' and @standalone='false']"):
		node.delete()
	for node in t.find(".//span[@class='orig' and @standalone='false']"):
		node.delete()
	for node in t.find(".//am"):
		node.delete()
	return t

def to_full(t):
	return t

if __name__ == "__main__":
	import sys
	t = tree.parse(sys.stdin)
	cleanup(t)
	sys.stdout.write(t.xml())
