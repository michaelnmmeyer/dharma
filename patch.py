from dharma import tree

def cover_text_with(root, tag_name):
	i = 0
	while i < len(root):
		node = root[i]
		if not isinstance(root[i], tree.String) or node.isspace():
			i += 1
			continue
		j = i + 1
		while j < len(root) and not isinstance(root[j], tree.Branch):
			j += 1
		node = tree.Tag(tag_name)
		node.extend(root[i:j])
		root.insert(i, node)
		i += 1

def process(t):
	for div in t.find(".//div[regex('^(edition|translation|commentary)$', @type)]"):
		cover_text_with(div, "p")
	for lst in t.find(".//list"):
		cover_text_with(lst, "item")

if __name__ == "__main__":
	t = tree.parse_string("<r>foo<i>bar</i>qux<!--hello-->bar</r>")
	cover_text_with(t.first("r"), "i")
	print(t.xml())
