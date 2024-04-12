from dharma import tree, parse, config
import bs4

def parse_xml(cell):
	t = tree.parse_string(f"<x>{cell}</x>", path="whatever")
	html = tree.html_format(t.first("x"), skip_root=True)
	p = parse.Parser(t)
	p.divs.append(set())
	p.push("block")
	p.dispatch_children(t.root)
	ret = p.pop()
	return ret, html

class Item:

	def __init__(self, description, markup, block, remark):
		self.description = description
		self.markup = markup
		self.block = block
		self.remark = remark

def parse_html():
	text = open("DHARMAEditorialConventionsdraft2024.html").read()
	soup = bs4.BeautifulSoup(text, "html.parser")
	for note_ref in soup.find_all("sup"):
		note_ref.decompose()
	def title_or_tag(node):
		return isinstance(node, bs4.Tag) and node.name in ("h2", "table")
	ret = []
	for node in soup.find_all(title_or_tag):
		if node.name == "h2":
			items = []
			ret.append((node.get_text(), items))
		else:
			rows = node.find_all("tr")[1:]
			for row in rows:
				cells = [td.get_text().strip() for td in row.find_all("td")]
				assert len(cells) == 4
				description, markup, _, remark = cells
				markup = markup.replace('”', '"')
				block, markup = parse_xml(markup)
				items.append(Item(description, markup, block, remark))
	return ret

