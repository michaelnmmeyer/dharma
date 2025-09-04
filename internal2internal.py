"""Internal transformations.

This fixes various things in the internal XML representation and produces three
displays: physical, logical, full.

Among other things, we remove all non-significant space from the input tree.

Summary of new elements.

We have two basic categories: inline elements (links and spans of text) and
block elements (divisions, paragraphs, etc.).

* Data fields: title, author, editor. These elements should not contain
paragraphs.

* Main divisions: summary, hand, edition, apparatus, translation, commentary,
bibliography.

* Other division: div.

* Paragraph-like: para, verse(>verse-line), head, quote.

* Containers: list(>item), dlist(>(key, value)), note.

* Inline elements: span, link, milestones (npage, nline, ncell).
"""



"""XXX TODO

at the root of divisions, cover everything with <p>

make a root div without anything else a div[@type='edition']
and make "textpart" optional in children of root divs.

# XXX document this and cleanup

# XXX among structural stuff to fix: nested divisions; we should allow them,
# because will be needed at some point, but be careful.


remove unknown elements in appropriate contexts. removing totally unknown elements is not the most useful, removing (or fixing) known elements that are being misused is important.


while parsing a paragraph: if we have a list, dlist or quote, move it one step up. They should be paragraph-level items.

number notes. will need this for rendering properly notes within the edition.

XXX for milestones, should keep a @n, but only a @n that is unique across the whole file (and that we thus need to preconstruct in some cases).

should ensure the uniqueness of @n across both npage and nline; ncell need not be numbered.

we can't tell in advance whether @n is unique across the whole file or across the textpart, so, after gathering all milestones, first check if they are unique across the whole file. if so, keep their @n as-is. otherwise, prefix the page number to the @n of nlines and check if unique. if so, stop there. otherwise, invent unique @n for each milestone.

# XXX should have an axis for "everything except <note>", because there are a
# lots of cases where we _must_ avoid <note>, and it's not immediately clear
# where, and it's error-prone.

# <p class="line"> to handle

"""



import re, sys
from dharma import tree, common

def is_division(node):
	if not isinstance(node, tree.Tag):
		return False
	return node.name in ("summary", "hand", "edition", "apparatus",
		"translation", "commentary", "bibliography", "div")

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
	milestones and <key>).

	Divisions that have a heading but no contents are also considered empty.
	We do not try to distinguish "default" headings (like "Apparatus", etc.)
	from non-default ones. Not sure how this should be made to work, because
	for <translation> we have several variations of "default" headings."""
	if len(root) == 0:
		if root.name not in ("document", "npage", "nline", "ncell", "key"):
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
				print([x.xml() for x in milestones], file=sys.stderr)
				print([x.xml() for x in tmp], file=sys.stderr)
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
	fix_milestones_location(t, milestones)
	check_milestones_valid(t, milestones)
	add_phantom_milestones(t, milestones)
	check_milestones_valid(t, milestones)
	add_milestones_breaks(t, milestones)
	check_milestones_valid(t, milestones)
	# XXX do this better
	for mile in milestones:
		mile["milestone-keep"] = "true"

def useful_milestones(t: tree.Tree):
	def inner(root, out):
		for node in root:
			if not isinstance(node, tree.Tag):
				continue
			match node.name:
				case "note" | "head":
					continue
				case "npage" | "nline" | "ncell":
					out.append(node)
				case _:
					inner(node, out)
	out = []
	if (root := t.first("/document/edition")):
		inner(root, out)
	return out

# Elements within which a milestone can appear. Note that these should *not*
# overlap.
milestone_accepting = ("para", "verse-line", "item", "key", "value", "quote")

def in_milestone_accepting(node):
	while True:
		parent = node.parent
		if not isinstance(parent, tree.Tag):
			return False
		if parent.name in ("span", "link"):
			node = parent
			continue
		if parent.name in milestone_accepting:
			return True
		return False

def fix_milestone_location(mile):
	match mile.parent.name:
		case "para" | "verse-line" | "item" | "key" | "value" | "quote" | "span":
			pass
		case "summary" | "hand" | "edition" | "apparatus" \
			| "translation" | "commentary" | "bibliography" | "div":
			tmp = tree.Tag("para")
			mile.insert_after(tmp)
			tmp.append(mile)
		case "verse":
			shift_milestones_in_verse(mile)
		case "list":
			shift_milestones_in_list(mile)
		case "dlist":
			shift_milestones_in_dlist(mile)
		case _:
			sys.stdout.write(mile.tree.xml())
			raise Exception(f"unexpected: milestone {mile!r} parent {mile.parent!r}")

def fix_milestones_location(t, milestones):
	"""Move milestones in appropriate spots.

        If the milestone appears at the beginning or at the end of an inline
        element (span or link), we move the milestone outside of this element.

        before or after (respectively) the parent element,
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

        moving up milestones must be done in a definite order, in two passes.
        iter milestones and move them up from left to right (for start) and the
        reverse (for end), then proceed with the upper level. if we end up in a
        non-inline, we should be within some kind of division; move the
        milestone forward if possible, otherwise move it backward, otherwise
        create a <p> at this location (and this <p> should be the only p within
        the edityion)
	"""
	milestones_ids = set(id(mile) for mile in milestones)
	move_up_milestones(t.root, milestones_ids)
	check_milestones_valid(t, milestones)
	# Milestones that are not in a milestone-accepting element. If the
	# milestone's parent is a division, wrap the milestone within a <p>.
	# XXX not enough, need to do that with other elements.
	for mile in milestones:
		fix_milestone_location(mile)

def is_milestone(node):
	return isinstance(node, tree.Tag) and node.name in ("npage", "nline", "ncell")

def shift_milestones(parent, skip, xpath):
	matching = parent.find(xpath)
	# Move all initial milestones to the beginning of the first container
	first = matching[0]
	j = 0
	while is_milestone(parent[skip]):
		first.insert(j, parent[skip])
		j += 1
	# Idem for terminal milestones
	last = matching[-1]
	j = 0
	while is_milestone(parent[-1]):
		last.insert(len(last) - j, parent[-1])
		j += 1

def shift_milestones_in_verse(mile):
	parent = mile.parent
	assert all(isinstance(elem, tree.Tag) for elem in parent)
	# We should have at least one <verse-line>, for holding the milestone.
	# Create one if need be.
	if not any(elem.name == "verse-line" for elem in parent):
		parent.append(tree.Tag("verse-line"))
	# Skip the heading, if any. Besides it, should only have as children
	# either milestones or verse-line.
	if parent[0].name == "verse-head":
		skip = 1
	else:
		skip = 0
	assert all(elem.name in ("npage", "nline", "ncell", "verse-line") for elem in parent[skip:]), parent.xml()
	return shift_milestones(parent, skip, "verse-line")

def shift_milestones_in_list(mile):
	parent = mile.parent
	assert all(isinstance(elem, tree.Tag) for elem in parent)
	# We should have at least one <item>, for holding the milestone.
	# Create one if need be.
	if not any(elem.name == "item" for elem in parent):
		parent.append(tree.Tag("item"))
	assert all(elem.name in ("npage", "nline", "ncell", "item") for elem in parent)
	return shift_milestones(parent, 0, "item")

def shift_milestones_in_dlist(mile):
	parent = mile.parent
	assert all(isinstance(elem, tree.Tag) for elem in parent)
	# We should have at least one <key>/<value> pair, for holding the
	# milestone. Create one if need be.
	if not any(elem.name == "value" for elem in parent):
		parent.append(tree.Tag("key"))
		parent.append(tree.Tag("value"))
	assert all(elem.name in ("npage", "nline", "ncell", "key", "value") for elem in parent)
	return shift_milestones(parent, 0, "*[name()='key' or name()='value']")

def move_up_milestones(root: tree.Tag, milestones_ids):
	assert isinstance(root, tree.Tag)
	for node in list(root):
		if not isinstance(node, tree.Tag) or node.name in ("npage", "nline", "ncell"):
			continue
		move_up_milestones(node, milestones_ids)
	if root.name not in ("span", "link"):
		return
	# We have an inline element (<span> or <link>). Move all milestones
	# at the beginning of the element to before the element; thus:
	#
	# 	before: foo <span><nline/><ncell/>bar</span> baz
	#	after:  foo <nline/><ncell/><span>bar</span> baz
	#
	# Idem for milestones at the end of the inline element.
	while len(root) > 0 and id(root[0]) in milestones_ids:
		root.insert_before(root[0])
	while len(root) > 0 and id(root[-1]) in milestones_ids:
		root.insert_after(root[-1])

def first_milestone_accepting_node(doc):
	def inner(root):
		for node in root:
			if not isinstance(node, tree.Tag):
				continue
			if node.name in milestone_accepting:
				return node
			ret = inner(node)
			if ret:
				return ret
	root = doc.first("/document/edition")
	assert root
	ret = inner(root)
	assert ret
	return ret

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
	insert = first_milestone_accepting_node(doc)
	i = 0
	units = ("npage", "nline", "ncell")
	while i < 3:
		unit = units[i]
		if len(insert) > i and isinstance(insert[i], tree.Tag) and insert[i].name == unit:
			assert len(milestones) > i
			assert insert[i] is milestones[i]
		else:
			mile = tree.Tag(unit, phantom="true")
			insert.insert(i, mile)
			milestones.insert(i, mile)
		i += 1
	assert i == 3
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
			if all(common.to_boolean(mile["break"], True) for mile in tmp):
				pass
			else:
				for mile in tmp:
					mile["break"] = "false"
		elif mile.name == "nline":
			tmp = [mile, next(miles)]
			assert tmp[1].name == "ncell"
			if all(common.to_boolean(mile["break"], True) for mile in tmp if mile["break"]):
				pass
			else:
				for mile in tmp:
					mile["break"] = "false"
		elif mile.name == "ncell":
			if not mile["break"]:
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
	"""Add spaces around milestones, where needed. If physical is False,
	only add spaces if @break=true; otherwise, take all milestones into account.
	This is only performed
	for milestones that have a @break that matches the boolean given as
	argument. (For the logical and full display, we only apply add spaces
	when @break=true, while for the physical display we add spaces for all
	values of @break.)
	"""
	# Note that @phantom milestones must be excluded (we don't
	# actually display them). Also note that we replace all milestones,
	# even the ones in the apparatus.
	for node in t.find(".//*[(name()='npage' or name()='nline' or name()='ncell') and not @phantom]"):
		assert isinstance(node, tree.Tag) # silence warnings
		if physical:
			# There is exactly one case in which we must not add
			# any spaces: ncell[@break="no"]
			if node.name == "ncell" and not common.to_boolean(node["break"], True):
				continue
		else:
			if not common.to_boolean(node["break"], True):
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
	"Unwraps tags that are not necessary for the physical display."
	for node in list(root):
		if not isinstance(node, tree.Tag):
			continue
		match node.name:
			case "note":
				# No recursion here, the node is part of the
				# text.
				pass
			case "display":
				if not node["name"]:
					pass
				elif node["name"] == "physical":
					unwrap_for_physical(node)
					node.unwrap()
				elif node["name"] == "logical":
					node.delete()
				else:
					raise Exception
			case "div" | "head" | "span" | "link" | "npage" | "nline" | "ncell":
				unwrap_for_physical(node)
			case "verse" | "dlist" | "list":
				unwrap_for_physical(node)
				node.unwrap()
			case "verse-head":
				node.delete()
			case "para" | "quote" | "key" | "value" | "item":
				unwrap_for_physical(node)
				node.prepend(" ")
				node.unwrap()
			case "verse-line":
				unwrap_for_physical(node)
				if common.to_boolean(node["break"]):
					node.prepend(" ")
				node.unwrap()
			case _:
				raise Exception(f"unexpected: {node!r}")

# People often use div[@type='textpart'] instead of page-like milestones for
# indicating physical divisions. We thus have a lot of inscriptions that
# have two textparts "Seal" and "Plates". In such cases, a new textpart means
# a new page-like division. But people also use textparts independently of
# page-like milestones. We can't tell what the user means, so do nothing
# special for now.
def wrap_for_physical(root, page=None, line=None):
	for node in list(root):
		if not isinstance(node, tree.Tag):
			if not page:
				page = tree.Tag("page")
				node.insert_before(page)
			if not line:
				line = tree.Tag("line")
				page.append(line)
			line.append(node)
			continue
		match node.name:
			case "div":
				page = line = None
				wrap_for_physical(node, page, line)
			case "head":
				page = line = None
			case "npage":
				page = tree.Tag("page")
				node.insert_before(page)
				head = tree.Tag("head")
				head.append(node)
				page.append(head)
				line = None
			case "nline":
				if not page:
					page = tree.Tag("page")
					node.insert_before(page)
				line = tree.Tag("line")
				page.append(line)
				line.append(node)
			case "ncell" | "span" | "link" | "note":
				if not page:
					page = tree.Tag("page")
					node.insert_before(page)
				if not line:
					line = tree.Tag("line")
					page.append(line)
				line.append(node)
			case _:
				raise Exception(f"unexpected: {node!r}")

# XXX in physical, differenciate between continuation lines and others?
# yes, a continuation page/line/cell is one that meets all following criteria:
# 1) appears at the beginning of a division
# 2) a milestone we generated viz. that the user did not specifify
# 3) is not the first npage/nline/ncell in the <edition>
# it is only created in wrap-for-physical, so do necessary stuff here.

def fix_lists_and_quotes(t: tree.Tree):
	for node in t.find(".//para/*[name()='list' or name()='dlist' or name()='quote']"):
		move_up_from_para(node)

# XXX for all stuff like this should find something more solid
def fix_misc(t: tree.Tree):
	for node in t.find(".//verse/para"):
		node.delete()

def move_up_from_para(node):
	para = node.parent
	assert isinstance(para, tree.Tag) and para.name == "para"
	left = tree.Tag("para")
	right = tree.Tag("para")
	buf = left
	for child in para:
		if child is node:
			buf = right
		else:
			buf.append(child)
	if len(left) > 0:
		para.insert_before(left)
	para.replace_with(node)
	if len(right) > 0:
		node.insert_after(right)

def add_hyphens(t):
	# We need to add a hyphen break after all the milestone @break=no,
	# whether or not there is a hyphen break at the end of the line.
	# (We also have preceding hyphens sometimes, but this is not OK I
	# think.)
	# Use <display><span tip="Hyphen break">-</span> at the end of each
	# line
	# Exclude phantom lines because we sometimes have:
	# foo<pb n="1" break="no"/><pb n="2" break="no"/>bar
	# In this case, we must add a hyphen after "foo", but in the phantom
	# line between pages 1 and 2.
	lines = t.find(".//line[not stuck-child::nline[@phantom]]")
	i = 1
	while i < len(lines):
		head = lines[i][0]
		if not isinstance(head, tree.Tag) or not head.name == "nline":
			i += 1
			continue
		if not common.to_boolean(head["break"], True):
			span = tree.Tag("span", tip="Hyphen break")
			span.append("-")
			lines[i - 1].append(span)
		i += 1

def split_around_milestone(inline, mile):
	"""We only perform a split on the first milestone. Thus, if there are
	several same-level milestones in a single span, this only takes into
	account the one given as argument (and the line/cell that immediately
	follow).
	"""
	left = None
	stack = []
	line = cell = None
	def inner(root):
		nonlocal left, stack, line, cell
		stack.append(tree.Tag(root.name, **root.attrs))
		i = 0
		while i < len(root):
			elem = root[i]
			if not isinstance(elem, tree.Tag):
				stack[-1].append(elem.copy())
				i += 1
				continue
			if elem is not mile:
				elem = inner(elem)
				stack[-1].append(elem)
				i += 1
				continue
			if mile.name == "npage":
				assert i < len(root) - 2 \
					and isinstance(root[i + 1], tree.Tag) \
					and root[i + 1].name == "nline" \
					and isinstance(root[i + 2], tree.Tag) \
					and root[i + 2].name == "ncell"
				line = root[i + 1]
				cell = root[i + 2]
				i += 3
			else:
				assert mile.name == "nline"
				assert i < len(root) - 1 \
					and isinstance(root[i + 1], tree.Tag) \
					and root[i + 1].name == "ncell"
				cell = root[i + 1]
				i += 2
			new_stack = []
			for tag in stack:
				new_stack.append(tree.Tag(tag.name, **tag.attrs))
			while len(stack) > 1:
				tag = stack.pop()
				stack[-1].append(tag)
			left = stack.pop()
			stack = new_stack
		return stack.pop()
	right = inner(inline)
	assert left
	assert mile.name == "npage" and line or line is None
	assert cell
	inline.insert_before(left)
	if mile.name == "npage":
		left.insert_after(mile)
		assert line
		mile.insert_after(line)
		line.insert_after(cell)
	else:
		assert mile.name == "nline"
		left.insert_after(mile)
		mile.insert_after(cell)
	cell.insert_after(right)
	inline.delete()

def fix_physical_inlines(t):
	milestones = t.find(".//*[@milestone-keep]")
	for mile in milestones:
		if mile.name == "ncell":
			# Cells should remain inlines
			continue
		inline = mile.parent
		if inline.name not in ("span", "link"):
			continue
		while True:
			parent = inline.parent
			if isinstance(parent, tree.Tag) and parent.name in ("span", "link"):
				inline = parent
			else:
				break
		split_around_milestone(inline, mile)

def to_physical(t):
	unwrap_for_physical(t)
	fix_spaces(t)
	fix_physical_inlines(t)
	wrap_for_physical(t)
	fix_milestones_spaces(t, physical=True)
	add_hyphens(t)
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

def number_notes(t):
	"""We number notes before we create the three displays, to make it
	easier later on to figure out which notes are duplicates."""
	notes = t.find("//note")
	for i, note in enumerate(notes, 1):
		note["n"] = str(i)

def process(t: tree.Tree):
	fix_misc(t)
	fix_spaces(t)
	fix_lists_and_quotes(t)
	fix_milestones(t)
	number_notes(t)
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
	for node in full.find(".//display[@name='physical']"):
		node.delete()
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
	for node in t.find(".//*[@milestone-keep]"):
		del node["milestone-keep"]
	for node in t.find(".//apparatus//display[@name='physical']"):
		node.delete()
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
