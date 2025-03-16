from dharma import tree

def cover_text_with(root, tag_name, start=0):
	assert start >= 0 and start < len(root)
	while start < len(root):
		node = root[start]
		if not isinstance(root[start], tree.String) or node.isspace():
			start += 1
			continue
		j = start + 1
		while j < len(root) and not isinstance(root[j], tree.Branch):
			j += 1
		node = tree.Tag(tag_name)
		node.extend(root[start:j])
		root.insert(start, node)
		start += 1

def process(t):
	# XXX not that simple, we allow <note> and <head> after headings
	# for textparts; and should not wrap in a p div[@type='textpart']
	# and see in EGD <pb/> "Blank outer page; the page beginning is not inside a block-level element §3.5.2."
	for div in t.find(".//div[regex('^(edition|translation|commentary)$', @type)]"):
		cover_text_with(div, "p")
	for lst in t.find(".//list"):
		cover_text_with(lst, "item")

if __name__ == "__main__":
	t = tree.parse_string("<r>foo<i>bar</i>qux<!--hello-->bar</r>")
	cover_text_with(t.first("r"), "i")
	print(t.xml())
