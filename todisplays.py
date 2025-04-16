from dharma import tree

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

