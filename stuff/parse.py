import os, sys, re, datetime
from dharma import tree

today = datetime.datetime.today().strftime("%Y-%m-%d")

THE_FILE = sys.argv[1]
match THE_FILE:
	case "vg1.xml":
		THE_TEMPLATE = "tpl1.xml"
		def mkident(ins):
			return f"DHARMA_INSMelKil{ins.ident:05}"
	case "vg2.xml":
		THE_TEMPLATE = "tpl2.xml"
		GN = 10000
		def mkident(ins):
			global GN
			GN += 1
			return f"DHARMA_INSTamilNadu{GN}"
	case "vg3.xml":
		THE_TEMPLATE = "tpl3.xml"
		GN = 20000
		def mkident(ins):
			global GN
			GN += 1
			return f"DHARMA_INSTamilNadu{GN}"
	case "vg4.xml":
		THE_TEMPLATE = "tpl4.xml"
		GN = 30000
		def mkident(ins):
			global GN
			GN += 1
			return f"DHARMA_INSTamilNadu{GN}"
	case "vg5.xml":
		THE_TEMPLATE = "tpl5.xml"
		GN = 40000
		def mkident(ins):
			global GN
			GN += 1
			return f"DHARMA_INSTamilNadu{GN}"

"""
pandoc cleaned.odt --wrap none -t tei -o cleaned.xml

java -jar ~/dharma/jars/trang.jar -O rnc cleaned.xml schema.rnc

"""

def handle_ins(ins):
	pass

class Inscription:

	def __init__(self):
		self.ident = -1
		self.summary = tree.Tree()
		self.edition = tree.Tag("p")
		self.edition.append("\n")
		self.translation = tree.Tree()

t = tree.parse(THE_FILE)

for div in t.find("//div"):
	div.unwrap()

for node in t.find("//hi[@rendition='simple:italic']"):
	node.name = "foreign"
	node.attrs.clear()

for node in t.find("//hi[@rendition='simple:bold']"):
	node.name = "hi"
	node.attrs.clear()
	node["rend"] = "bold"

for node in t.find("//hi[@rendition='simple:superscript']"):
	node.unwrap()

for node in t.find("//note/p"):
	if not isinstance(node[0], tree.String):
		continue
	node[0].replace_with(node[0].strip())
for node in t.find("//note"):
	assert all(child.name == "p" for child in node.find("*"))
	for child in list(node):
		if isinstance(child, tree.String):
			assert child.isspace()
			child.delete()
	if len(node) == 0:
		node.delete()
	elif len(node) == 1:
		node.first("p").unwrap()

def iter_strings(node, ignore_notes=False):
	match node:
		case tree.String():
			yield node
		case tree.Tag() if ignore_notes and node.name == "note":
			pass
		case tree.Tag() | tree.Tree():
			for kid in node:
				yield from iter_strings(kid, ignore_notes=True)

def strings(node):
	return list(iter_strings(node))

section = None
inscriptions = []
ins = Inscription()
for p in t.find("/root/*[name()='p' or name()='head']"):
	if p.empty:
		continue
	if p.name == "head":
		getattr(ins, section).append(p)
		continue
	text = p.text()
	if text.startswith("#"):
		ins = Inscription()
		inscriptions.append(ins)
		m = re.match(r"^#([0-9]+)[^.]*\.\s*", text)
		assert m, text
		ins.ident = int(m.group(1))
		ins.summary.append(p)
		section = "summary"
		continue
	if text.startswith("<<<"):
		section = text.strip("<").strip()
		assert section in ("summary", "edition", "translation")
		continue
	if section == "summary":
		m = re.match(r"^\(.+?\)", text)
		if m:
			section = "edition"
		else:
			ins.summary.append(p)
			continue
	if section == "edition":
		m = re.match(r"^\((.+?)\)", text)
		if m:
			lb = tree.Tag("lb", n=m.group(1))
			ins.edition.append(lb)
			assert p[0].startswith(m.group())
			if THE_FILE == "vg5.xml" and p[0].removeprefix(m.group()) == p[0].removeprefix(m.group()).lstrip():
				lb["break"] = "no"
			p[0].replace_with(p[0].removeprefix(m.group()).strip())
			ins.edition.extend(p)
			ins.edition.append("\n")
			continue
		else:
			section = "translation"
	if section == "translation":
		ins.translation.append(p)
		continue
	assert 0

def fix_vowels(s):
	def repl(m):
		return m.group(1).upper()
	return re.sub(r"˚([aāiīuūeēoō])", repl, s, flags=re.I)

def is_vowel(c):
	import unicodedata
	return unicodedata.normalize("NFD", c.lower())[0] in "aeiou"

def fix_vowels2(root):
	space = True
	for s in strings(root):
		for i in range(len(s)):
			c = s.data[i]
			if c.isspace():
				space = True
			elif space and is_vowel(c):
				tmp = tree.String(s[:i] + c.upper() + s[i + 1:])
				s.replace_with(tmp)
				s = tmp
				space = False
			else:
				space = False


def add_gaps(s):
	ret = tree.Tag("root")
	i = 0
	for m in re.finditer(r"[X](\s+[X])*", s):
		start, end = m.start(), m.end()
		n = sum(not c.isspace() for c in m.group())
		ret.append(s[i:start])
		ret.append(" ")
		ret.append(tree.Tag("gap", reason="lost", quantity=str(n), unit="character"))
		ret.append(" ")
		i = end
	ret.append(s[i:])
	ret.coalesce()
	return ret

def replace_delimited_in(root, start, end, tag):
	assert isinstance(root, tree.Branch)
	nodes = list(root)
	x = 0
	while x < len(nodes):
		node = nodes[x]
		if not isinstance(node, tree.String):
			x += 1
			continue
		i = str(node).find(start)
		if i < 0:
			x += 1
			continue
		y = x
		j = str(node).find(end, i + len(start))
		if j < 0:
			y += 1
			while y < len(nodes):
				node = nodes[y]
				if not isinstance(node, tree.String):
					y += 1
					continue
				j = str(node).find(end)
				if j >= 0:
					break
				y += 1
		if j < 0:
			x += 1
			continue
		if x == y:
			node = nodes[x]
			tmp = tree.Tag("tmp")
			tmp.append(node[:i])
			repl = tag.copy()
			repl.append(node[i + len(start):j])
			tmp.append(repl)
			tmp.append(node[j + len(end):])
			nodes[x] = tmp[-1]
			node.replace_with(tmp)
			tmp.unwrap()
			continue
		repl = tag.copy()
		repl.append(nodes[x][i + len(start):])
		for node in nodes[x + 1:y]:
			repl.append(node)
		repl.append(nodes[y][:j])
		tmp = tree.String(nodes[x][:i])
		nodes[x].replace_with(tmp)
		nodes[x] = tmp
		tmp = tree.String(nodes[y][j + len(end):])
		nodes[y].replace_with(tmp)
		nodes[y] = tmp
		nodes[x].insert_after(repl)
		x = y

def replace_delimited(root, start, end, tag):
	replace_delimited_in(root, start, end, tag)
	for node in root:
		if not isinstance(node, tree.Tag):
			continue
		replace_delimited(node, start, end, tag)

def replace_choices(root):
	assert root.name == "unclear"
	# [abc*] <supplied reason="omitted">abc</supplied>
	if THE_FILE == "vg5.xml" and isinstance(root[-1], tree.String) and root[-1].endswith("*"):
		root.name = "supplied"
		root.attrs.clear()
		root["reason"] = "omitted"
		root[-1].replace_with(root[-1][:-1])
		return
	choice = tree.Tag("choice")
	unclear = tree.Tag("unclear")
	choice.append(unclear)
	for node in root:
		if not isinstance(node, tree.String):
			unclear.append(node.copy())
			continue
		chunks = node.split("/")
		for i, chunk in enumerate(chunks):
			if i > 0:
				unclear = tree.Tag("unclear")
				choice.append(unclear)
			unclear.append(chunk)
	if len(choice) > 1:
		root.replace_with(choice)

def process_ins(ins, ident):
	out = tree.parse(THE_TEMPLATE)
	out.first("//idno").append(ident)
	out.first("//change[@who='part:mime']")["when"] = today
	# summary
	tmp = out.first("//summary")
	tmp.extend(ins.summary)
	tmp.append("\n\n")
	tmp.coalesce()
	# edition
	tmp = out.first("//div[@type='edition']")
	tmp.append(ins.edition)
	tmp.append("\n\n")
	tmp.coalesce()
	for gr in tmp.find(".//foreign"):
		gr.name = "hi"
		gr["rend"] = "grantha"
	tmp.coalesce()
	for s in strings(tmp):
		s.replace_with(fix_vowels(s.data))
	tmp.coalesce()
	if THE_FILE == "vg5.xml":
		fix_vowels2(tmp)
	tmp.coalesce()
	for s in strings(tmp):
		r = add_gaps(s.data)
		s.replace_with(r)
		r.unwrap()
	replace_delimited(tmp, "[[", "]]", tree.Tag("dbracket"))
	replace_delimited(tmp, "[", "]", tree.Tag("unclear"))
	tmp.coalesce()
	for unclear in tmp.find(".//unclear"):
		replace_choices(unclear)
	tmp.coalesce()
	# translation
	tmp = out.first("//div[@type='translation']")
	tmp.extend(ins.translation)
	tmp.coalesce()
	replace_delimited(tmp, "[[", "]]", tree.Tag("dbracket"))
	replace_delimited(tmp, "[", "]", tree.Tag("supplied", reason="subaudible"))
	replace_delimited(tmp, "(", ")", tree.Tag("supplied", reason="explanation"))
	# all
	out.coalesce()
	replace_delimited(out, "{{", "}}", tree.Tag("supplied", reason="lost"))
	for db in out.find(".//dbracket"):
		db.insert_before("[[")
		db.insert_after("]]")
		db.unwrap()
	out = out.xml()
	out = re.sub(r"(…|\.\.\.)(…|\.)*", '<gap reason="lost" extent="unknown" unit="character"/>', out)
	out = re.sub(r" +", " ", out)
	return out

"""TODO

write common function that seeks delimitors properly: {{x}}, [x], (x)

partout:
	{{abc}} supplied reason=lost

dans la trad:
	[abc] supplied reason=subaudible
	(abc) supplied reason=explanation

dans l'édition:
	[ab/cd] <choice><unclear>ab</unclear><unclear>cd</unclear></choice>
	[abc] <unclear>abc</unclear>
"""

for f in os.listdir("out"):
	path = os.path.join("out", f)
	os.remove(path)
for ins in inscriptions:
	ident = mkident(ins)
	path = f"out/~{ident}.xml"
	with open(path, "w") as f:
		f.write(process_ins(ins, ident))
