from dharma import tree, parse, common, langs, texts
import bs4, copy

tpl = """
<TEI>
<text><body>
<div type="{context}" xml:lang="eng">
{code}
</div>
</body></text>
</TEI>
"""

def parse_xml(context, code):
	t = tree.parse_string(tpl.format(context=context, code=code), path="whatever")
	langs.assign_languages(t)
	html = tree.html_format(t.first(f"//div[@type='{context}']"), skip_root=True)
	p = parse.Parser(t)
	p.dispatch_children(t.root)
	if context == "translation":
		block = p.document.translation[0]
	else:
		block = p.document.edition
	return block.render_full(), html

class Item:

	def __init__(self, description, markup, block, remark, type):
		self.description = description
		self.markup = markup
		self.block = block
		self.remark = remark
		self.type = type

def is_heading(node):
	if not isinstance(node, bs4.Tag):
		return  False
	tag = node.name
	return len(tag) == 2 and tag[0] == "h" and tag[1] >= "1" and tag[1] <= "6"

def parse_html():
	f = texts.File("project-documentation", "website/editorial-conventions.md")
	html = common.pandoc(f.text)
	soup = bs4.BeautifulSoup(html, "html.parser")
	title = soup.find("h1")
	if title:
		page_title = "".join(t.get_text() for t in title)
		title.decompose()
	else:
		page_title = "Untitled"
	for title in soup.find_all("h6"):
		title.name = "div"
		title.attrs.clear()
		title.attrs["class"] = ["card-heading"]
		div = soup.new_tag("div", **{"class": "card-body"})
		node = title.next_sibling
		while node is not None and not is_heading(node):
			if isinstance(node, bs4.Tag) and node.name == "pre":
				if "translation" in node.attrs.get("class", []):
					context = "translation"
				else:
					context = "edition"
				display, pretty_xml = parse_xml(context, node.get_text())
				demo = soup.new_tag("div", **{"class": "edition-demo"})
				code = soup.new_tag("pre", **{"class": "xml"})
				code.append(bs4.BeautifulSoup(pretty_xml, "html.parser"))
				rendered = soup.new_tag("div", **{"class": ["ed",
					context == "edition" and "full" or "translation"]})
				rendered.append(bs4.BeautifulSoup(display, "html.parser"))
				demo.append(code)
				demo.append(rendered)
				div.append(demo)
			else:
				div.append(copy.copy(node))
			next = node.next_sibling
			if isinstance(node, bs4.Tag):
				node.decompose()
			else:
				node.extract()
			node = next
		title.insert_after(div)
	for code in soup.find_all("code"):
		code.attrs.setdefault("class", []).append("xml")
	return page_title, str(soup)

if __name__ == "__main__":
	@common.transaction("texts")
	def main():
		parse_html()
	main()
