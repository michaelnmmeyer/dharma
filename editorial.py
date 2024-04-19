from dharma import tree, parse, config, langs
import bs4

tpl = """
<TEI>
<text><body>
<div type="edition" xml:lang="eng">
{context}
</div>
</body></text>
</TEI>
"""

def parse_xml(cell):
	t = tree.parse_string(tpl.format(context=cell), path="whatever")
	langs.assign_languages(t)
	html = tree.html_format(t.first("//div[@type='edition']"), skip_root=True)
	p = parse.Parser(t)
	p.dispatch_children(t.root)
	ret = p.document.edition
	return ret, html

class Item:

	def __init__(self, description, markup, block, remark, type):
		self.description = description
		self.markup = markup
		self.block = block
		self.remark = remark
		self.type = type

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
			title = node.get_text().strip()
			if not title:
				continue
			items = []
			ret.append((title, items))
		else:
			rows = node.find_all("tr")[1:]
			for row in rows:
				cells = [td.get_text().strip() for td in row.find_all("td")]
				assert len(cells) == 4
				description, markup, _, remark = cells
				markup = markup.replace('”', '"')
				type = "edition"
				if "translation" in title.lower():
					type = "translation"
				block, markup = parse_xml(markup)
				items.append(Item(description, markup, block, remark, type))
	return ret
