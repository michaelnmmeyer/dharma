# Remains to try to pair lemmas and apparatus together.

import sys, unicodedata, re, html, io, os
from bs4 import BeautifulSoup, NavigableString
from dharma import persons

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
		DOC["edition"] = []
		DOC["translation"] = []
		DOC["apparatus"] = []
		DOC["commentary"] = []
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
		DOC[DIV] = []
	elif level in (5, 6):
		pass

current_fmt = 0

def append(buf, s, fmt=0):
	global current_fmt
	close = current_fmt & ~fmt
	if close & ITALIC:
		buf.append("</foreign>")
	if close & APPARATUS:
		#buf.append("</app>")
		pass
	open = ~current_fmt & fmt
	if open & APPARATUS:
		#buf.append("<app>")
		pass
	if open & ITALIC:
		buf.append("<foreign>")
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
			if DIV == "apparatus":
				fmt &= ~APPARATUS
			append(buf, text, fmt)
	append(buf, "", 0)
	buf = "".join(buf).strip()
	if not buf:
		return
	if DIV == "apparatus":
		if buf[0].isdigit():
			num, rest = buf.split(None, 1)
			num = num.rstrip(".")
			p = rest.find("◇")
			if p < 0:
				p = rest.find(":")
			if p < 0:
				lemma, notes = "???", rest
			else:
				lemma, notes = rest[:p], rest[p + 1:]
				lemma = lemma.strip()
				notes = notes.strip()
			buf = []
			buf.append(f'<app loc="{num}">')
			buf.append(f'<lem>{lemma}</lem>')
			buf.append(f'<note>{notes}</note>')
			buf.append('</app>')
			buf = "\n".join(buf)
		else:
			buf = "<!-- %s -->" % buf
	elif DIV == "edition":
		match = re.match(r"\s*\((.+?)\)\s*(.+)", buf)
		if match:
			num = match.group(1).strip()
			rest = match.group(2).strip()
			buf = []
			if DOC[DIV] and DOC[DIV][-1][-1] == "-":
				buf.append(f'<lb break="no" n="{num}"/> {rest}')
			else:
				buf.append(f'<lb n="{num}"/> {rest}')
			buf = "\n".join(buf)
	elif DIV == "translation" or DIV == "commentary":
		buf = "<p>%s</p>" % buf
	DOC[DIV].append(buf)
	
def authors_list(ids):
	if len(ids) == 1:
		return persons.plain(ids[0])
	if len(ids) == 2:
		return "%s and %s" % tuple(persons.plain(id) for id in ids)
	if len(ids) == 3:
		return "%s, %s and %s" % tuple(persons.plain(id) for id in ids)
	assert 0

for para in all_paras(soup):
	if para.name == "h":
		process_header(para)
	else:
		process_para(para)


TPL = open("tpl.xml").read()

rets = []
for doc in DOCS:
	tpl = TPL
	eds = []
	for ed in doc["editors"]:
		ed = persons.xml(ed, "persName")
		eds.append(str(ed))
	eds = "\n".join(eds)
	buf = []
	if doc["introduction"]:
		buf.append("<!--")
		buf.append("\n".join(doc["introduction"]))
		buf.append("-->")
	if doc["edition"]:
		buf.append('<div type="edition" xml:lang="kaw-Latn">')
		buf.append('<p>')
		buf.append("\n".join(doc["edition"]))
		buf.append('</p>')
		buf.append('</div>')
	if doc["apparatus"]:
		buf.append('<div type="apparatus">')
		buf.append("\n".join(doc["apparatus"]))
		buf.append('</div>')
	if doc["translation"]:
		buf.append('<div type="translation" xml:lang="eng">')
		buf.append("\n".join(doc["translation"]))
		buf.append('</div>')
	if doc["commentary"]:
		buf.append('<div type="commentary">')
		buf.append("\n".join(doc["commentary"]))
		buf.append('</div>')
	body = "\n".join(buf)
	tpl = tpl.replace("{{title}}", doc["title"])
	tpl = tpl.replace("{{persons}}", eds)
	tpl = tpl.replace("{{body}}", body)
	tpl = tpl.replace("{{authors_list}}", authors_list(doc["editors"]))
	name = doc["title"].split()[0].lower()
	rets.append((name, tpl))

for i, (name, contents) in enumerate(rets, 1):
	name = "%02d_%s.xml" % (i, name)
	print(name)
	base, _ = os.path.splitext(name)
	contents = contents.replace("{{filename}}", base)
	with open(os.path.join("texts", name), "w") as f:
		f.write(contents)
