import re
from dharma import tree

# Summary of new elements:
#
# ¶ data fields: title, author, editor
# (these elements should not contain paragraphs)
#
# ¶ divisions: summary, hand, edition, apparatus, translation, commentary,
# bibliography, div
# (all their children strings should be removed)
#
# ¶ para-like: para verse(>verse-line) head quote
#
# ¶ para containers: dlist(>(key, value)) list(>item) note
#
# ¶ sub-paragraphs divisions: item, key, value, verse-line
# (can only contain inline)
#
# ¶ inline: span link
#
# ¶ milestones: npage nline ncell

# Whitespace fixing
#
# We basically do what follows. We remove spaces at the beginning and at the end
# of each; furthermore, we squeeze spaces (collapse sequences of spaces into a
# single space).
#
# We transfer spaces at the beginning and at the end of a subtree to the parent
# element, recursively. Thus,
#
#	<para>foo<span><link> bar</link></span></para>
#
# is turned into:
#
#	<para>foo <span><link>bar</link></span></para>
#
# We only do that for "span" and "link" (inline tags, per contrast with
# block-level ones). For "note" tags, we drop preceding whitespace. For all
# other tags, we drop spaces both before and after them.
#
# Finally, we delete all empty elements except the tree's root viz. "document"
# and milestones.

def fix_spaces(doc: tree.Tree):
	_, root, _ = handle_subtree(doc.root)
	doc.root.replace_with(root)
	return doc

# space is one of "add", "drop", "keep".
# * add: a space character should be added here, but if preceded by drop, then
# don't add one.
# * drop: remove all following spaces
# * keep: preserve whitespace in the output
def handle_subtree(root: tree.Tag):
	buf = tree.Tag(root.name, **root.attrs)
	left_space = "keep"
	space = "drop"
	first = True
	for node in root:
		match node:
			case tree.String():
				if first:
					if len(node) == 0:
						continue
					left_space = space = handle_string(buf, space, node)
					first = False
				else:
					space = handle_string(buf, space, node)
			case tree.Tag():
				if first:
					left_space, space = handle_tag(buf, space, node)
					first = False
				else:
					_, space = handle_tag(buf, space, node)
	# Delete all empty nodes except the root tag and milestones.
	if len(buf) == 0:
		match root.name:
			case "npage" | "nline" | "ncell" | "document":
				pass
			case _:
				buf = None
	return left_space, buf, space

def handle_string(buf, space, node):
	match space:
		case "add":
			text = squeeze(node.data.lstrip())
			if len(text) == 0:
				return "add"
			add_space(buf)
		case "drop":
			text = squeeze(node.data.lstrip())
			if len(text) == 0:
				return "drop"
		case "keep":
			text = squeeze(node.data)
			if len(text) == 0:
				return "keep"
			if text == " ":
				return "add"
			if text[0].isspace():
				add_space(buf)
				text = text[1:]
	if text[-1].isspace():
		text = text[:-1]
		buf.append(text)
		return "add"
	buf.append(text)
	return "keep"

def handle_tag(buf, space, node):
	left_space, repl, right_space = handle_subtree(node)
	if len(buf) > 0:
		match space:
			case "add":
				match left_space:
					case "add" | "keep":
						add_space(buf)
			case "drop":
				if is_space(buf[-1]):
					buf.pop()
			case "keep":
				match left_space:
					case "add":
						add_space(buf)
	if repl:
		buf.append(repl)
	match node.name:
		case "note":
			return "drop", space
		case "span" | "link":
			return left_space, right_space
		case _:
			return "drop", "drop"

def squeeze(s):
	return re.sub(r"\s+", " ", s)

def add_space(buf):
	#buf.append(tree.Tag("space"))
	buf.append(" ")

def is_space(node):
	# match node:
	# 	case tree.Tag(name_="space"):
	# 		return True
	# 	case _:
	# 		return False
	return isinstance(node, str) and str(node) == " "

"""
for physical:

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








"""
use a convention for the placement of pbs, etc.



furthermore, milestones should only appear at the start of an element. when they are located

---

gather all milestones in a list. then traverse the list.

1) apply placement conventions

for each milestone.

if the milestone appears at the very beginning or end of an element, move the milestone to the parent element as much as possible _but_ stop as soon as the parent is one of: para verse-line item key value quote. milestones should only appear within one of these. in practice, we should only move up from inline elements (span, link), must be checked; probably best to move up only while the parent is an inline (span, link) _and_ while the milestone is at the beginning/end of this inline.

if the milestone is not within one of the milestone-accepting elements, move it forward to the beginning of the next element (viz. following::*, but note that we might leave an empty element if the element only contains the milestone) until this element is one of those that can hold a milestone (but skip <note> and its descendants). exception if the milestone is a ncell and appears at the very end of the edition, in which case leave it where it is.

what about consecutive npages, etc.?

2) complete milestones

nodes = [<npage>, <npage>, etc.]
insert = first insertion point in <edition> viz. start of first para|verse-line|...
	when the edition is empty, might not have any insert point;
	in this case return
npage = nline = ncell = None

cur = insert
if cur not immediately followed by a npage
	insert an npage after it, cur=npage
else
	cur = next
if cur not immediately followed by a nline
	insert an nline after it, cur=nline
else
	cur = next
if cur not immediately followed by a ncell
	insert an ncell after it, cur=ncell
else
	cur = next

cur = next(nodes)
if cur is npage
	if cur not immediately followed by nline
		insert a nline after it, cur=nline
	else
		cur = the following nline
	if cur not immediately followed by a ncell:
		insert a ncell after it, cur=ncell
	else
		cur = next
elif cur is nline
	if cur not immediately followed by a ncell:
		insert a ncell after it, cur=ncell
	else
		cur = next
elif cur is ncell
	pass



---

we have to allocate phantom pages/lines/cells, when a) the encoding is incorrect; b) the encoding is correct but a category is missing. it is best to keep these phantom elements in the output than to remove them, for search.

except that if they occur within "head" or "note, leave them as-is (viz. replace them with <span> and don't consider them meaningful). and also replace them with <span> when they appear outside of the edition

we can't really tell whether numbering is continuous between textparts or not, so if we have:
	<pb n=X>foo<div type="textpart">bar<pb n=Z>
we assume that page X continues in the next textpart (instead of assuming that the next textpart is missing a <pb n=Y> at the very beginning). to represent the fact that page X continues in the next textpart, use a cont=true flag in the first div we generate within the next textpart.

when generating the search representation, not sure what to do with the textpart heading in the middle. might want to index separately the TOC (with all headings)
and the text (without interruption).

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
	import os, sys
	from dharma import tei2internal, common, texts

	@common.transaction("texts")
	def main():
		path = os.path.abspath(sys.argv[1])
		f = texts.File("/", path)
		doc = tei2internal.process_file(f)
		t = doc.serialize()
		t = fix_spaces(t)
		sys.stdout.write(t.xml())
	try:
		main()
	except BrokenPipeError:
		pass
