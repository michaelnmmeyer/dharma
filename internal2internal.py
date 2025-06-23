import re, sys
from dharma import tree, common

"""
Summary of new elements:

¶ data fields: title, author, editor
(these elements should not contain paragraphs)
¶ divisions: summary, hand, edition, apparatus, translation, commentary,
bibliography, div
(all their children strings should be removed)
¶ para-like: para verse(>verse-line) head quote
¶ para containers: dlist(>(key, value)) list(>item) note
¶ sub-paragraphs divisions: item, key, value, verse-line
(can only contain inline)
¶ inline: span link
¶ milestones: npage nline ncell
"""

"""
XXX

remove unknown elements in appropriate contexts. removing totally unknown elements is not the most useful, removing (or fixing) known elements that are being misused is important.


while parsing a paragraph: if we have a list, dlist or quote, move it one step up. They should be paragraph-level items.

number notes. will need this for rendering properly notes within the edition.


"""

# XXX should have an axis for "everything except <note>", because there are a
# lots of cases where we _must_ avoid <note>, and it's not immediately clear
# where, and it's error-prone.

# XXX fix invalid nesting of para with lg, etc. and write appropriate rnc schema and
# try to validate all files after the transforms to ensure we do transforms correctly.

# XXX handle notes in the edition (handle the multiple displays) ; use e.g. http://localhost:8023/texts/INSKarnataka00007

# <p class="line"> to handle

"""
XXX for milestones, should keep a @n, but only a @n that is unique across the whole file (and that we thus need to preconstruct in some cases).

should ensure the uniqueness of @n across both npage and nline; ncell need not be numbered.

we can't tell in advance whether @n is unique across the whole file or across the textpart, so, after gathering all milestones, first check if they are unique across the whole file. if so, keep their @n as-is. otherwise, prefix the page number to the @n of nlines and check if unique. if so, stop there. otherwise, invent unique @n for each milestone.



"""

def fix_spaces(doc: tree.Tree):
	"""Whitespace normalization.

	We basically do what follows. We remove spaces at the beginning and at
	the end of each element (except if the element is an inline). Thus, no
	element starts or ends with a space. Furthermore, we squeeze spaces
	(collapse sequences of spaces into a single space within each element).
	If the element is an inline, we transfer spaces at the beginning and at
	the end of a subtree to the parent element, recursively. Thus,

	        <para>foo<span><link> bar</link></span></para>

	is turned into:

	        <para>foo <span><link>bar</link></span></para>

	For "note" tags, we drop preceding whitespace. For all other tags, we
	drop spaces both before and after them.

	Finally, we delete all empty elements except the tree's root viz.
	<document> and milestones (<npage>, <nline>, <ncell>).
	"""
	fix_elements(doc.root)

def add_space_before(root):
	parent = root.parent
	i = parent.index(root)
	if i > 0 and isinstance(parent[i - 1], tree.String):
		node = parent[i - 1]
		if len(node) > 0 and node[-1].isspace():
			pass
		else:
			node.replace_with(node.data + " ")
	else:
		parent.insert(i, " ")

def add_space_after(root):
	parent = root.parent
	i = parent.index(root)
	if i < len(parent) - 1 and isinstance(parent[i + 1], tree.String):
		node = parent[i + 1]
		if len(node) > 0 and node[0].isspace():
			pass
		else:
			node.replace_with(" " + node.data)
	else:
		parent.insert(i + 1, " ")

def starts_with_space(s):
	return len(s) > 0 and s[0].isspace()

def ends_with_space(s):
	return len(s) > 0 and s[-1].isspace()

def delete_if_empty(root: tree.Tag):
	"""Delete all empty elements (except the XML document's root and
	milestones).

	Divisions that have a heading but no contents are also considered empty.
	We do not try to distinguish "default" headings (like "Apparatus", etc.)
	from non-default ones. Not sure how this should be made to work, because
	for <translation> we have several variations of "default" headings."""
	if len(root) == 0:
		if root.name not in ("document", "npage", "nline", "ncell"):
			root.delete()
	elif len(root) == 1 and isinstance(root[0], tree.Tag) and root[0].name == "head":
		root.delete()

def fix_elements(root: tree.Tag):
	nodes = []
	for node in root:
		if isinstance(node, tree.Tag):
			nodes.append(node)
	for node in nodes:
		fix_elements(node)
	root.coalesce(recursive=False)
	nodes.clear()
	for node in root:
		if isinstance(node, (tree.Tag, tree.String)):
			nodes.append(node)
	forward_spaces = root.name in ("span", "link")
	for i, node in enumerate(nodes):
		if not isinstance(node, tree.String):
			continue
		repl = squeeze(node.data)
		assert len(repl) > 0
		if i < len(nodes) - 1 and ends_with_space(repl) \
			and isinstance(nodes[i + 1], tree.Tag) \
			and nodes[i + 1].name not in ("span", "link"):
			repl = repl.rstrip()
		if i > 0 and starts_with_space(repl) \
			and isinstance(nodes[i - 1], tree.Tag) \
			and nodes[i - 1].name not in ("span", "link", "note"):
			repl = repl.lstrip()
		if i == 0 and starts_with_space(repl):
			repl = repl.lstrip()
			if forward_spaces:
				add_space_before(root)
		if i == len(nodes) - 1 and len(repl) > 0 and repl[-1] == " ":
			repl = repl.rstrip()
			if forward_spaces:
				add_space_after(root)
		if not repl:
			node.delete()
		elif repl != node.data:
			node.replace_with(repl)
	delete_if_empty(root)

def squeeze(s):
	return re.sub(r"\s+", " ", s)


################################ Milestones ####################################

def check_milestones_valid(t, milestones):
	if __debug__:
		tmp = useful_milestones(t)
		tmpl = [id(x) for x in tmp]
		for x in milestones:
			if not id(x) in tmpl:
				print(x.xml())
		assert len(milestones) == len(tmp)
		for i, (m, n) in enumerate(zip(milestones, tmp)):
			if m is not n:
				print(f"diff at {i}", file=sys.stderr)
				print(milestones[i].xml(), file=sys.stderr)
				print(tmp[i].xml(), file=sys.stderr)
				print(milestones, file=sys.stderr)
				print(tmp, file=sys.stderr)
				raise Exception

def fix_milestones(t):
	"""The point of these transformations (besides display-related stuff)
	is to ensure all editions have the same milestones structure.

	After transforms, we have a hierarchy: page > line > cell, where each
	inscription that has an edition has 1+ page(s); where each page contains
	1+ line(s); and where each line contains 1+ cell(s). Thus each
	inscription that does have an edition contains at least three
	milestones: one page, one line, one cell. We add "phantom" pages, lines
	and cells as needed to cover the whole text.
	"""
	milestones = useful_milestones(t)
	if not milestones:
		return
	add_phantom_milestones(t, milestones)
	check_milestones_valid(t, milestones)
	add_milestones_breaks(t, milestones)
	check_milestones_valid(t, milestones)

def useful_milestones(doc: tree.Tree):
	return doc.find("/document/edition//*[(name()='npage' or name()='nline' or name()='ncell') and not ancestor::*[name()='note' or name()='head']]")

milestone_accepting = ("para", "verse-line", "item", "key", "value", "quote")

def in_milestone_accepting(node):
	for parent in node.find("ancestor::*"): # XXX nesting? and also <note>
		if isinstance(parent, tree.Tag) and parent.name in milestone_accepting:
			return True
	return False

def first_milestone_accepting(node):
	for anchor in node.find("following::*"): # XXX nesting? and also <note>
		if anchor.name in milestone_accepting:
			return anchor

def fix_milestones_location(milestones):
	"""Apply placement conventions for each milestone.

	milestone-accepting elements: para verse-line item key value quote
	        note that these should *not* overlap

	inline elements: span link

	1) If the milestone appears at the very beginning or end of an element,
	   move the milestone before or after (respectively) the parent element,
	   and repeat as much as possible, stopping as soon as the parent is a
	   milestone-accepting element. Milestones should only appear within one
	   of these. In practice, we should only move up from inline elements,
	   but this must be checked. Probably simpler to move it up only while
	   the parent is an inline element *and* while the milestone is at the
	   beginning/end of this inline.

	Problem: moving things up would not work properly if we do some
	transformations on the contents (add a prefix or suffix), as in:

	        <supplied><lb n="1"/>foo</supplied>

	        <span class="supplied" tip="Lost text">[<nline
	        break="true"><span tip="Line
	        number">⟨1⟩</span></nline>foo]</span>

	To fix this, we wrap the added contents within <display> and treat this
	tag as empty while moving up the milestone, thus:

	        <supplied><lb n="1"/>foo</supplied>

	        ... results in:

	        <span class="supplied" tip="Lost
	        text"><display>[</display><nline break="true"><span tip="Line
	        number">⟨1⟩</span></nline><span>foo</span><display>]</display></span>

	        ... which results in:

	        <nline break="true"><span tip="Line
	        number">⟨1⟩</span></nline><span class="supplied" tip="Lost
	        text"><display>[</display><span>foo</span><display>]</display></span>

	Another (maybe preferable) solution would be to leave the displayed
	milestone in place and move up only a structural element (which would
	not be displayed).

	2) If the milestone is not within one of the milestone-accepting
	   elements, move it forward to the beginning of the next
	   milestone-accepting element (in following::* order) (but skip <note>
	   and its descendants). Exception if the milestone appears at the very
	   end of the edition: in this case, leave it where it is. But what if
	   the milestone is outside of a <p>?

	What about consecutive npages, etc.? We need to create an extra <p> for
	them, but we should do this only when rendering the physical display.

	        <para> <span> A <span><npage/>B</span> C </span> </para>

	        <para> A <span> B <npage/> </span> </para>
	"""
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

def is_milestone(node):
	return isinstance(node, tree.Tag) and node.name in ("npage", "nline", "ncell")

def fix_milestones_location2(root: tree.Tag):
	for node in list(root):
		if not isinstance(node, tree.Tag) or is_milestone(node):
			continue
		fix_milestones_location2(node)
	if root.name not in ("span", "link"):
		return
	while len(root) > 0 and is_milestone(root[0]):
		root.insert_before(root[0])
	while len(root) > 0 and is_milestone(root[-1]):
		root.insert_after(root[-1])

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

def add_phantom_milestones(doc: tree.Tree, milestones):
	"""
	We have to allocate phantom pages/lines/cells, when (a) the encoding is
	incorrect; (b) the encoding is correct but a category is missing. it is
	best to keep these phantom elements in the output than to remove them,
	for search.

	except that if they occur within "head" or "note, leave them as-is (viz.
	replace them with <span> and don't consider them meaningful). and also
	replace them with <span> when they appear outside of the edition

	we can't really tell whether numbering is continuous between textparts
	or not, so if we have:

	        <pb n=X>foo<div type="textpart">bar<pb n=Z>

	we assume that page X continues in the next textpart (instead of
	assuming that the next textpart is missing a <pb n=Y> at the very
	beginning). to represent the fact that page X continues in the next
	textpart, use a cont=true flag in the first div we generate within the
	next textpart.

	when generating the search representation, not sure what to do with the
	textpart heading in the middle. might want to index separately the TOC
	(with all headings) and the text (without interruption).
	"""
	for node in doc.find("/document/edition//*"):
		if node.name in milestone_accepting:
			insert = node
			break
	else:
		raise Exception
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
	i = 3
	while i < len(milestones):
		mile = milestones[i]
		if mile.name == "npage":
			if (tmp := mile.first("following-sibling::*")) and tmp.name == "nline":
				mile = tmp
			else:
				tmp = tree.Tag("nline", phantom="true")
				mile.insert_after(tmp)
				mile = tmp
				milestones.insert(i + 1, tmp)
			if (tmp := mile.first("following-sibling::*")) and tmp.name == "ncell":
				mile = tmp
			else:
				tmp = tree.Tag("ncell", phantom="true")
				mile.insert_after(tmp)
				mile = tmp
				milestones.insert(i + 2, tmp)
			i += 3
		elif mile.name == "nline":
			if (tmp := mile.first("following-sibling::*")) and tmp.name == "ncell":
				pass
			else:
				tmp = tree.Tag("ncell", phantom="true")
				mile.insert_after(tmp)
				milestones.insert(i + 1, tmp)
			i += 2
		elif mile.name == "ncell":
			i += 1
		else:
			raise Exception

def add_milestones_breaks(doc, milestones):
	"""Add missing @break to each milestone and make @break consistent.

	* The 3 initial milestones (at the very beginning of the first
	milestone-accepting element) must have @break="yes".

	* The last ncell, which is necessarily a ncell, must have @break="yes".
	Idem for the preceding nline and npage if they appear right before the
	ncell, without any text or other tag in-between.

	* Otherwise, we must necessarily have coherent milestones for sequences
	npage+nline+ncell or nline+ncell; if there is a break="false" among any
	of these, it was explicitly specified in the original TEI, so set
	@break="false" to all other milestones accordingly.
	"""
	assert len(milestones) >= 3
	assert milestones[0].name == "npage"
	assert milestones[1].name == "nline"
	assert milestones[2].name == "ncell"
	for mile in milestones[:3]:
		mile["break"] = "true"
	miles = iter(milestones[3:])
	for mile in miles:
		if mile.name == "npage":
			tmp = [mile, next(miles), next(miles)]
			assert tmp[1].name == "nline"
			assert tmp[2].name == "ncell"
			if all(common.from_boolean(mile["break"]) for mile in tmp):
				pass
			else:
				for mile in tmp:
					mile["break"] = "false"
		elif mile.name == "nline":
			tmp = [mile, next(miles)]
			assert tmp[1].name == "ncell"
			if all(common.from_boolean(mile["break"]) for mile in tmp if mile["break"]):
				pass
			else:
				for mile in tmp:
					mile["break"] = "false"
		elif mile.name == "ncell":
			mile["break"] = "false"
		else:
			raise Exception
	cell = milestones[-1]
	if milestone_is_terminal(doc, cell):
		cell["break"] = "true"
		if (line := cell.first("stuck-preceding-sibling::nline")):
			line["break"] = "true"
			if (page := line.first("stuck-preceding-sibling::npage")):
				page["break"] = "true"

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

def milestone_at_block_start(node):
	while True:
		parent = node.parent
		assert isinstance(parent, tree.Tag)
		i = parent.index(node)
		if i > 0:
			return False
		if parent.name not in ("span", "link"):
			return True
		node = parent

def milestone_at_block_end(node):
	while True:
		parent = node.parent
		assert isinstance(parent, tree.Tag)
		i = parent.index(node)
		if i < len(parent) - 1:
			return False
		if parent.name not in ("span", "link"):
			return True
		node = parent

def fix_milestones_spaces(t: tree.Branch, physical=False):
	"""Add spaces around milestones, where needed. This is only performed
	for milestones that have a @break that matches the boolean given as
	argument. (For the logical and full display, we only apply add spaces
	when @break=true, while for the physical display we add spaces for all
	values of @break.)
	"""
	# Note that @phantom milestones must be excluded.
	for node in t.find(".//*[(name()='npage' or name()='nline' or name()='ncell') and not @phantom]"):
		if not physical and not common.to_boolean(node["break"], True):
			continue
		if not milestone_at_block_start(node):
			node.prepend(" ")
		if not milestone_at_block_end(node):
			node.append(" ")


########################### Physical Display ###################################

# XXX TODO for physical:
# wrap lines within <para>
# split these elements if needed: a, para

def unwrap_for_physical(root: tree.Branch):
	"Unwraps tag not necessary for the physical display."
	for node in list(root):
		if not isinstance(node, tree.Tag):
			continue
		match node.name:
			case "note":
				pass
			case "div" | "head" | "span" | "link" | "npage" | "nline" | "ncell":
				unwrap_for_physical(node)
			case "verse":
				unwrap_for_physical(node)
				node.unwrap()
			case "verse-head":
				node.delete()
			case _:
				assert node.name in ("para", "verse-line", "quote", "dlist", "key", "value", "list", "item")
				node.unwrap()

"""
SPACING!!!!
key + ' ' + value
verse-line + '- ' + verse-line
div
(all their children strings should be removed)
¶ para-like: para verse(>verse-line) head quote
¶ para containers: dlist(>(key, value)) list(>item) note
¶ sub-paragraphs divisions: item, key, value, verse-line
(can only contain inline)
¶ inline: span link
¶ milestones: npage nline ncell

"""

# People often use div[@type='textpart'] instead of page-like milestones for
# indicating physical divisions. We thus have a lot of inscriptions that
# have two textparts "Seal" and "Plates". In such cases, a new textpart means
# a new page-like division. But people also use textparts independently of
# page-like milestones. We can't tell what the user means, so do nothing
# special for now.
def wrap_for_physical(root, page=None, line=None):
	for node in list(root):
		match node:
			case tree.Tag("div"):
				page = line = None
				wrap_for_physical(node, page, line)
			case tree.Tag("head"):
				page = line = None
			case tree.Tag("npage"):
				page = tree.Tag("page")
				node.insert_before(page)
				head = tree.Tag("head")
				head.append(node)
				page.append(head)
				line = None
			case tree.Tag("nline"):
				if not page:
					page = tree.Tag("page")
					node.insert_before(page)
				line = tree.Tag("line")
				page.append(line)
				line.append(node)
			case tree.Tag("ncell") | tree.Tag("span") | tree.Tag("link") \
				| tree.Tag("note") | tree.String():
				if not page:
					page = tree.Tag("page")
					node.insert_before(page)
				if not line:
					line = tree.Tag("line")
					page.append(line)
				line.append(node)
			case _:
				raise Exception(f"unexpected: {node!r}")

def add_hyphens(t):
	lines = t.find(".//line")
	i = 1
	while i < len(lines):
		head = lines[i][0]
		assert isinstance(head, tree.Tag) and head.name == "nline"
		if not common.to_boolean(head["break"], True):
			span = tree.Tag("span", tip="Hyphen break")
			span.append("-")
			lines[i - 1].append(span)
		i += 1

def to_physical(t):
	unwrap_for_physical(t)
	wrap_for_physical(t)
	fix_milestones_spaces(t, physical=True)
	add_hyphens(t)
	# We need to add a hyphen break after all the milestone @break=no,
	# whether or not there is a hyphen break at the end of the line.
	# (We also have preceding hyphens sometimes, but this is not OK I
	# think.)
	# Use <display><span tip="Hyphen break">-</span> at the end of each
	# line
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

def process(t: tree.Tree):
	fix_spaces(t)
	fix_milestones(t)
	# And create the three displays.
	edition = t.first("/document/edition")
	if not edition:
		return t
	full = edition.copy()
	full.name = "full"
	if (head := full.first("head")):
		head.delete()
	physical = full.copy()
	physical.name = "physical"
	to_physical(physical)
	fix_milestones_spaces(full)
	logical = full.copy()
	logical.name = "logical"
	to_logical(logical)
	head = edition.first("head")
	edition.clear()
	fix_milestones_spaces(t)
	if head:
		edition.append(head)
	edition.append(physical)
	edition.append(logical)
	edition.append(full)
	return t

def make_pretty_printable(t: tree.Tree):
	t.coalesce()
	# Make spaces apparent around tags.
	for s in t.strings():
		if s[0] == " ":
			s.insert_before(tree.Comment("space"))
		if s[-1] == " " and len(s) > 1:
			s.insert_after(tree.Comment("space"))
	for node in t.find("//display"):
		node.unwrap()

if __name__ == "__main__":
	import os, sys
	from dharma import tei2internal, common, texts

	@common.transaction("texts")
	def main():
		path = os.path.abspath(sys.argv[1])
		f = texts.File("/", path)
		t = tei2internal.process_file(f).serialize()
		t = process(t)
		make_pretty_printable(t)
		sys.stdout.write(t.xml())
	try:
		main()
	except BrokenPipeError:
		pass
