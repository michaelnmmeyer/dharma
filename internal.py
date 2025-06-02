import re
from dharma import tree, common

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
# of each element. Furthermore, we squeeze spaces (collapse sequences of spaces
# into a single space within each element.
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

#XXX REPR add tests for clean_spaces (TestInternalSpaces)

# space is one of "add", "drop", "keep".
# ¶ add: a space character should be added here, but if preceded by drop, then
# don't add one.
# ¶ drop: remove all following spaces
# ¶ keep: preserve whitespace in the output
def handle_subtree(root: tree.Tag):
	buf = tree.Tag(root.name, **root.attrs)
	left_space = space = "drop"
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
	# Delete all empty nodes except the root tag (needed for producing a
	# valid XML document) and milestones (they are meaningful on their own,
	# without contents)
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
		case _:
			assert 0
			return
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
	match buf.name:
		case "note":
			left_space, right_space = "drop", space
		case "span" | "link":
			pass # use the child's values
		case _:
			left_space = right_space = "drop"
	return left_space, right_space

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
The resulting hierarchy must be:
	<page>
		<line>
			<cell>
				<link>
				<span>
"""


"""
Apply placement conventions for each milestone.

milestone-accepting elements: para verse-line item key value quote
	note that these should *not* overlap

inline elements: span link

1) If the milestone appears at the very beginning or end of an element, move the milestone before or after (respectively) the parent element, and repeat as much as possible, stopping as soon as the parent is a milestone-accepting element. Milestones should only appear within one of these. In practice, we should only move up from inline elements, but this must be checked. Probably simpler to move it up only while the parent is an inline element *and* while the milestone is at the beginning/end of this inline.

Problem: moving things up would not work properly if we do some transformations on the contents (add a prefix or suffix), as in:

	<supplied><lb n="1"/>foo</supplied>

	<span class="supplied" tip="Lost text">[<nline break="true"><span tip="Line number">⟨1⟩</span></nline>foo]</span>

To fix this, we wrap the added contents within <display> and treat this tag as empty while moving up the milestone, thus:

	<supplied><lb n="1"/>foo</supplied>

	... results in:

	<span class="supplied" tip="Lost text"><display>[</display><nline break="true"><span tip="Line number">⟨1⟩</span></nline><span>foo</span><display>]</display></span>

	... which results in:

	<nline break="true"><span tip="Line number">⟨1⟩</span></nline><span class="supplied" tip="Lost text"><display>[</display><span>foo</span><display>]</display></span>

Another (maybe preferable) solution would be to leave the displayed milestone in place and move up only a structural element (which would not be displayed).

2) If the milestone is not within one of the milestone-accepting elements, move it forward to the beginning of the next milestone-accepting element (in following::* order) (but skip <note> and its descendants). Exception if the milestone is a ncell and appears at the very end of the edition: in this case, leave the milestone where it is.



What about consecutive npages, etc.? We need to create an extra <p> for them, but we should do this only when rendering the physical display.

	<para> <span> A <span><npage/>B</span> C </span> </para>

	<para> A <span> B <npage/> </span> </para>
"""
milestone_accepting = ("para", "verse-line", "item", "key", "value", "quote")

def in_milestone_accepting(node):
	for parent in node.find("ancestor::*"): # XXX nesting
		if parent.name in milestone_accepting:
			return True
	return False

def first_milestone_accepting(node):
	for anchor in node.find("following::*"): # XXX nesting
		if anchor.name in milestone_accepting:
			return anchor

def fix_milestones_location(doc: tree.Tree):
	milestones = doc.find("/document/edition//*[name()='npage' or name()='nline' or name()='ncell' and not ancestor::note]")
	for mile in milestones:
		parent = mile.parent
		while isinstance(parent, tree.Tag) and parent.name in ("span", "link"):
			if front_node(parent) is mile:
				parent.insert_before(mile)
			elif back_node(parent) is mile:
				parent.insert_after(mile)
			else:
				break
			parent = parent.parent
		if not in_milestone_accepting(mile) and (anchor := first_milestone_accepting(mile)):
			anchor.prepend(mile)

def front_node(node):
	for child in node:
		if isinstance(child, tree.Tag) and child.name == "display":
			continue
		return child

def back_node(node):
	for child in reversed(node):
		if isinstance(child, tree.Tag) and child.name == "display":
			continue
		return child

def expand_useless_milestones(doc: tree.Tree):
	keep = set()
	for mile in doc.find("/document/edition//*[(name()='npage' or name()='nline' or name()='ncell') and not ancestor::*[name()='note' or name()='head']]"):
		keep.add(mile)
	for mile in doc.find("//*[name()='npage' or name()='nline' or name()='ncell']"):
		if mile not in keep:
			mile.unwrap()

"""
We have to allocate phantom pages/lines/cells, when a) the encoding is incorrect; b) the encoding is correct but a category is missing. it is best to keep these phantom elements in the output than to remove them, for search.

except that if they occur within "head" or "note, leave them as-is (viz. replace them with <span> and don't consider them meaningful). and also replace them with <span> when they appear outside of the edition

we can't really tell whether numbering is continuous between textparts or not, so if we have:
	<pb n=X>foo<div type="textpart">bar<pb n=Z>
we assume that page X continues in the next textpart (instead of assuming that the next textpart is missing a <pb n=Y> at the very beginning). to represent the fact that page X continues in the next textpart, use a cont=true flag in the first div we generate within the next textpart.

when generating the search representation, not sure what to do with the textpart heading in the middle. might want to index separately the TOC (with all headings)
and the text (without interruption).
"""
def add_phantom_milestones(doc: tree.Tree):
	edition = doc.first("/document/edition")
	if not edition:
		return
	milestones = edition.find(".//*[name()='npage' or name()='nline' or name()='ncell']")
	for node in edition.find(".//*"):
		if node.name in milestone_accepting:
			insert = node
			break
	else:
		assert not milestones
		return
	if len(insert) > 0 and isinstance(insert[0], tree.Tag) and insert[0].name == "npage":
		assert len(milestones) > 0
		assert insert[0] is milestones[0]
	else:
		mile = tree.Tag("npage", phantom="true")
		insert.insert(0, mile)
		milestones.insert(0, mile)
	if len(insert) > 1 and isinstance(insert[1], tree.Tag) and insert[1].name == "nline":
		assert len(milestones) > 1
		assert insert[1] is milestones[1]
	else:
		mile = tree.Tag("nline", phantom="true")
		insert.insert(1, mile)
		milestones.insert(1, mile)
	if len(insert) > 2 and isinstance(insert[2], tree.Tag) and insert[2].name == "ncell":
		assert len(milestones) > 2
		assert insert[2] is milestones[2]
	else:
		mile = tree.Tag("ncell", phantom="true")
		insert.insert(2, mile)
		milestones.insert(2, mile)
	for mile in milestones[3:]:
		if mile.name == "npage":
			if (tmp := mile.first("following-sibling::*")) and tmp.name == "nline":
				mile = tmp
			else:
				tmp = tree.Tag("nline", phantom="true")
				mile.insert_after(tmp)
				mile = tmp
			if (tmp := mile.first("following-sibling::*")) and tmp.name == "ncell":
				mile = tmp
			else:
				tmp = tree.Tag("ncell", phantom="true")
				mile.insert_after(tmp)
				mile = tmp
		elif mile.name == "nline":
			if (tmp := mile.first("following-sibling::*")) and tmp.name == "ncell":
				pass
			else:
				tmp = tree.Tag("ncell", phantom="true")
				mile.insert_after(tmp)
		elif mile.name == "ncell":
			pass
		else:
			raise Exception
	if __debug__:
		milestones = edition.find(".//*[name()='npage' or name()='nline' or name()='ncell']")
		assert len(milestones) >= 3
		assert milestones[0].name == "npage"
		assert milestones[1].name == "nline"
		assert milestones[2].name == "ncell"
		assert milestones[-1].name == "ncell"

"""
Add missing @break to each milestone and make @break consistent.

¶ The 3 initial milestones (at the very beginning of the first
milestone-accepting element) must have @break="yes".

¶ If there is a milestone at the very end of the text (at the very end of the
last milestone-accepting element), it must have @break="yes".

¶ Otherwise, we must necessarily have coherent milestones for sequences
npage+nline+ncell or nline+ncell; if there is a break="false" among any of
these, it was explicitly specified in the original TEI, so set @break="false"
to all other milestones accordingly.
"""
def add_milestones_breaks(doc: tree.Tree):
	milestones = doc.find("/document/edition//*[name()='npage' or name()='nline' or name()='ncell']")
	if not milestones:
		return
	for mile in milestones[:3]:
		mile["break"] = "true"
	miles = iter(milestones[3:])
	for mile in miles:
		if mile.name == "npage":
			tmp = [mile, next(miles), next(miles)]
			if all(common.from_boolean(mile["break"]) for mile in tmp):
				pass
			else:
				for mile in tmp:
					mile["break"] = "false"
		elif mile.name == "nline":
			tmp = [mile, next(miles)]
			if all(common.from_boolean(mile["break"]) for mile in tmp if mile["break"]):
				pass
			else:
				for mile in tmp:
					mile["break"] = "false"
		elif mile.name == "ncell":
			pass
		else:
			assert 0
	mile = milestones[-1]
	if milestone_is_terminal(doc, mile):
		mile["break"] = "true"
	else:
		mile["break"] = "false"

def milestone_is_terminal(doc, mile):
	"""Whether this milestone (which must be a cell) occurs at the very end
	of the text"""
	assert mile.name == "ncell"
	last = None
	for node in doc.find("//*"):
		if node.name not in milestone_accepting:
			continue
		last = node
	return last is mile

"""
under /document/edition, unwrap everything except: div, head, span, link, npage,
nline, ncell, note. should remove only: para, verse verse-line head quote dlist key value list item

XXX TODO
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
"""
def unwrap_for_physical(root: tree.Branch):
	for node in list(root):
		if not isinstance(node, tree.Tag):
			continue
		match node.name:
			case "note":
				continue
			case "div" | "head" | "span" | "link" | "npage" | "nline" | "ncell":
				unwrap_for_physical(node)
			case "verse-head":
				node.delete()
			case _:
				assert node.name in ("para", "verse", "verse-line", "head", "quote", "dlist", "key", "value", "list", "item")
				node.unwrap()

def to_physical(t):
	unwrap_for_physical(t)
	for node in t.find(".//span[@class='corr' and @standalone='false']"):
		node.delete()
	for node in t.find(".//span[@class='reg' and @standalone='false']"):
		node.delete()
	for node in t.find(".//ex"):
		node.delete()

def to_logical(t):
	for node in t.find(".//span[@class='sic' and @standalone='false']"):
		node.delete()
	for node in t.find(".//span[@class='orig' and @standalone='false']"):
		node.delete()
	for node in t.find(".//am"):
		node.delete()

def to_full(t):
	pass

def process(t: tree.Tree):
	fix_spaces(t)
	print(t.xml())
	exit()
	fix_spaces(t)
	expand_useless_milestones(t)
	fix_milestones_location(t)
	add_phantom_milestones(t)
	add_milestones_breaks(t)
	edition = t.first("/document/edition")
	if not edition:
		return t
	full = edition.copy()
	full.name = "full"
	if (head := full.first("head")):
		head.delete()
	to_full(full)
	physical = full.copy()
	physical.name = "physical"
	to_physical(physical)
	logical = full.copy()
	logical.name = "logical"
	to_logical(logical)
	head = edition.first("head")
	edition.clear()
	if head:
		edition.append(head)
	edition.append(physical)
	edition.append(logical)
	edition.append(full)
	return t

if __name__ == "__main__":
	import os, sys
	from dharma import tei2internal, common, texts

	@common.transaction("texts")
	def main():
		path = os.path.abspath(sys.argv[1])
		f = texts.File("/", path)
		t = tei2internal.process_file(f).serialize()
		t = process(t)
		sys.stdout.write(t.xml())
	try:
		main()
	except BrokenPipeError:
		pass
