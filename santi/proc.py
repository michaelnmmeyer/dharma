# Remains to try to pair lemmas and apparatus together.

import sys, unicodedata, re, html, io, os
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
		if color in ("pink", "violet"):
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

path = "santi.xml"
with open(path) as f:
	text = unicodedata.normalize("NFC", f.read())
soup = BeautifulSoup(io.StringIO(text), "xml")
collect_styles(soup)

with open("tpl.xml") as f:
	tree = BeautifulSoup(f, "xml")

# 2 = text title
# 3/4 = main div: text (= edition) apparatus, commentary, translation
# 5,6 = div

in_introduction = True

EDITORS = {
	"TKD": "tykd",
	"WJS": "wjsa",
	"AG": "argr",
}

DOCS = []
DOC = None
DIV = None

def process_header(h):
	global DOC, DIV
	text = h.get_text().strip()
	if not text:
		return
	global in_introduction
	if in_introduction:
		if text != "Taji Gunung (910-12-21)":
			return
		in_introduction = False
	level = int(h["text:outline-level"])
	if level == 2:
		DOC = {}
		DOC["title"] = text
		DOCS.append(DOC)
		DIV = "introduction"
		DOC[DIV] = []
	elif level in (3, 4):
		if text.startswith("Text"):
			editors = []
			for ed in re.findall(r"[A-Z]+", text.removeprefix("Text")):
				editors.append(EDITORS[ed])
			DOC["editors"] = editors
			DIV = "edition"
		else:
			assert text in ("Apparatus", "Translation", "Commentary")
			DIV = text.lower()
		assert not DIV in DOC
		DOC[DIV] = []
	elif level in (5, 6):
		pass

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

def process_para(para):
	global DOC, DIV
	assert para.name == "p"
	if not DIV:
		return
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
	if not buf:
		return
	print(DOC)
	DOC[DIV].append("".join(buf))

for para in all_paras(soup):
	if para.name == "h":
		process_header(para)
	else:
		process_para(para)

exit()

code = "\n".join(code) + "\n"
parts = """Taji Gunung (910-12-21)
Wuru Tunggal (912-03-08)
Timbanan Wungkal (913-02-11)
Pesindon I and II (914-08-14)
Tulang Er III (914-12-30)
Tihang (914-11-08)
Wintang Mas II (919-10-12)
Sugih Manek (915-09-13)
Barahasrama (915-12-14)
Kiringan (917-11-14)
Lintakan (841 Śaka, 919-07-12)
Gilikan (date lost)
Air Kali (849-850 Śaka)
""".strip().splitlines()

locs = [code.index(p) for p in parts] + [len(code)]
chunks = [code[locs[i]:locs[i + 1]] for i in range(len(locs) - 1)]

for i, (name, chunk) in enumerate(zip(parts, chunks), 1):
	name = "%02d_%s.txt" % (i, name.split()[0].lower())
	print(name)
	with open(os.path.join("texts", name), "w") as f:
		f.write(chunk)
