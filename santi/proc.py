import sys, unicodedata
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

APP_STYLES = set()

def check_styles(soup):
	for style in soup.find_all("style"):
		color = "black"
		props = style.find("text-properties")
		if props:
			color = COLORS[props.get("fo:color", "#000000")]
			if color == "pink":
				APP_STYLES.add(style["style:name"])

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
soup = BeautifulSoup(open(path), "xml")
check_styles(soup)

in_app = False

def append(buf, s, is_app=False):
	global in_app
	if in_app:
		if not is_app:
			in_app = False
			buf.append(">")
	else:
		if is_app:
			in_app = True
			buf.append("<")
	buf.append(s)

for para in all_paras(soup):
	if para.name == "h":
		text = para.get_text().strip()
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
			if chunk.get("text:style-name") in APP_STYLES:
				append(buf, text, True)
			else:
				append(buf, text)
	append(buf, "", False)
	buf = "".join(buf).strip().replace("\n", " ")
	buf = unicodedata.normalize("NFC", buf)
	if not buf:
		continue
	print(buf)
