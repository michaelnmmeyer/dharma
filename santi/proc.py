import sys, unicodedata, re, html, io
from bs4 import BeautifulSoup, NavigableString

COLORS = {
	"#ff00ff": "pink",

	"#fb0207": "red",
	"#ff0000": "red",
	"#fb0207": "red",

	"#800080": "violet",
	"#9900ff": "violet",

	"#1155cc": "blue", # hyperlink
	"#1a73e8": "blue",
	"#1a73e8": "blue",
	"#0000ff": "blue",
	"#0070c0": "blue",

	"#000000": "black",
	"#434343": "black",
	"#3c4043": "black",
}

def all_paras(soup):
	def is_para(t):
		return t.name == "p" or t.name == "h"
	return soup.find_all(name=is_para)

APPARATUS = 1 << 0
ITALIC = 1 << 1

STYLES = {}

def collect_styles(soup):
	for style in soup.find_all("style"):
		color = "black"
		props = style.find("text-properties")
		if not props:
			continue
		name = style["style:name"]
		fmt = 0
		color = COLORS[props.get("fo:color", "#000000")]
		if color == "pink":
			fmt |= APPARATUS
		if props.get("fo:font-style") == "italic":
			fmt |= ITALIC
		assert not name in STYLES
		STYLES[name] = fmt

def span_to_string(chunk):
	buf = []
	assert chunk.name == "span", chunk
	for item in chunk:
		if isinstance(item, NavigableString):
			buf.append(item)
		elif item.name == "tab":
			buf.append("\t")
		elif item.name == "line-break":
			buf.append("\n")
		elif item.name in ("annotation",):
			continue
		elif item.name == "note": # footnote; keep?
			continue
		elif item.name == "s":
			buf.append(" ")
		else:
			assert 0, item
	return "".join(buf)

path = sys.argv[1]
with open(path) as f:
	text = unicodedata.normalize("NFC", f.read())
soup = BeautifulSoup(io.StringIO(text), "xml")
collect_styles(soup)

current_fmt = 0

def append(buf, s, fmt=0):
	global current_fmt
	close = current_fmt & ~fmt
	if close & ITALIC:
		buf.append("</i>")
	if close & APPARATUS:
		buf.append("</app>")
	open = ~current_fmt & fmt
	if open & APPARATUS:
		buf.append("<app>")
	if open & ITALIC:
		buf.append("<i>")
	buf.append(html.escape(s))
	current_fmt = fmt

for para in all_paras(soup):
	if para.name == "h":
		text = para.get_text().strip()
		text = html.escape(text)
		print(text)
		continue
	assert para.name == "p"
	buf = []
	for chunk in para:
		if chunk.name in ("annotation-end", "soft-page-break", "bookmark",
			"annotation", "change-start", "change-end"):
			continue
		if chunk.name == "tab":
			append(buf, "\t")
			continue
		if chunk.name == "s":
			append(buf, " ")
			continue
		if chunk.name == "line-break":
			append(buf, "\n")
			continue
		if chunk.name == "a":
			assert chunk.span
			chunk = chunk.span
		if isinstance(chunk, NavigableString):
			append(buf, chunk)
		else:
			assert chunk.name == "span", chunk
			text = span_to_string(chunk)
			fmt = STYLES[chunk["text:style-name"]]
			append(buf, text, fmt)
	append(buf, "", 0)
	buf = "".join(buf).replace("\n", " ")
	buf = buf.replace(" </app>", "</app> ")
	buf = buf.replace(" </i>", "</i> ")
	buf = buf.replace("<app> ", " <app>")
	buf = buf.replace("<i> ", " <i>")
	buf = re.sub(r"\s+", " ", buf).strip()
	if not buf:
		continue
	print(buf)
