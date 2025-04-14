from dharma import tree

"""
for physical:

traverse the tree in order, and make a stack of:
	npage
	nline
	ncell
we will have to allocate phantom pages for inscriptions that start with a line.
at the end of the parse, if we haven't found a single explicit page, unwrap the
single page we have. and do the same with phantom lines and cells.

except that if they occur within one of these, leave them as-is.
	head
	note

unwrap:
	para
	verse
	verse-line
	list
	dlist

split if needed:
	a
	para

keep as is:
	div


<page>
	<line>
		<cell>
			<a>
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
			case "a" | "span":
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

