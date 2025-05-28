import os, sys, re, datetime
from dharma import tree

today = datetime.datetime.today().strftime("%Y-%m-%d")

"""
pandoc cleaned.odt -t tei -o cleaned.xml

java -jar ~/dharma/jars/trang.jar -O rnc cleaned.xml schema.rnc

default namespace = ""

start = element root { p+ }
p =
  element p {
    (text
     | element hi {
         attribute rendition { xsd:NMTOKEN },
         text
       }
     | element note { p? })+
  }

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

t = tree.parse("cleaned.xml")

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
	assert isinstance(node[0], tree.String)
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
for p in t.find("/root/p"):
	if p.empty:
		continue
	text = p.text()
	if text.startswith("#"):
		ins = Inscription()
		inscriptions.append(ins)
		m = re.match(r"^#([0-9]+)[^.]*\.\s*", text)
		assert m
		ins.ident = int(m.group(1))
		ins.summary.append(p)
		section = "summary"
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

def fix_paren(t):
	for foreign in t.find(".//foreign"):
		parent = foreign.parent
		i = parent.index(foreign)
		if i >= 1 and isinstance(parent[i - 1], tree.String) and parent[i - 1].endswith("("):
			pass
		else:
			continue
		if i < len(parent) - 1 and isinstance(parent[i + 1], tree.String) and parent[i + 1].startswith(")"):
			pass
		else:
			continue
		parent[i - 1].replace_with(parent[i - 1][:-1])
		parent[i + 1].replace_with(parent[i + 1][1:])
		supplied = tree.Tag("supplied", reason="explanation")
		foreign.insert_before(supplied)
		supplied.append(foreign)

def fix_unclear(s):
	ret = tree.Tag("root")
	i = 0
	for m in re.finditer(r"\[([^[].*?)\]", s):
		start, end = m.start(), m.end()
		ret.append(s[i:start])
		text = m.group(1)
		chunks = text.split("/")
		# [abc] <unclear>abc</unclear>
		# [ab/cd] <choice><unclear>ab</unclear><unclear>cd</unclear></choice>
		if len(chunks) == 1:
			tmp = tree.Tag("unclear")
			tmp.append(text)
		else:
			tmp = tree.Tag("choice")
			for chunk in chunks:
				unclear = tree.Tag("unclear")
				unclear.append(chunk)
				tmp.append(unclear)
		ret.append(tmp)
		i = end
	ret.append(s[i:])
	ret.coalesce()
	return ret

def fix_supplied(s):
	ret = tree.Tag("root")
	i = 0
	for m in re.finditer(r"\{\{(.+?)\}\}", s):
		start, end = m.start(), m.end()
		ret.append(s[i:start])
		tmp = tree.Tag("supplied", reason="lost")
		tmp.append(m.group(1))
		ret.append(tmp)
		i = end
	ret.append(s[i:])
	ret.coalesce()
	return ret

def process_ins(ins):
	out = tree.parse("tpl.xml")
	out.first("//idno").append(mkident(ins))
	out.first("//change[@who='part:mime']")["when"] = today
	tmp = out.first("//summary")
	tmp.extend(ins.summary)
	tmp.append("\n\n")
	tmp.coalesce()
	tmp = out.first("//div[@type='edition']")
	tmp.append(ins.edition)
	tmp.append("\n\n")
	tmp.coalesce()
	for gr in tmp.find(".//foreign"):
		gr.name = "hi"
		gr["rend"] = "grantha"
	for s in strings(tmp):
		r = fix_unclear(s.data)
		s.replace_with(r)
		r.unwrap()
	tmp.coalesce()
	for s in strings(tmp):
		s.replace_with(fix_vowels(s.data))
	tmp.coalesce()
	for s in strings(tmp):
		r = add_gaps(s.data)
		s.replace_with(r)
		r.unwrap()
	tmp = out.first("//div[@type='translation']")
	tmp.extend(ins.translation)
	fix_paren(tmp)
	tmp.coalesce()
	out.coalesce()
	for s in strings(out):
		r = fix_supplied(s.data)
		s.replace_with(r)
		r.unwrap()
	out = out.xml()
	out = out.replace("‡", '<g type="kaḻañcu"/>')
	out = re.sub(r"(…|\.\.\.)(…|\.)*", ' <gap reason="lost" extent="unknown" unit="character"/> ', out)
	out = re.sub(r" +", " ", out)
	return out

def mkident(ins):
	return f"DHARMA_INSMelKil{ins.ident:05}"

for ins in inscriptions:
	ident = mkident(ins)
	path = f"out/~{ident}.xml"
	with open(path, "w") as f:
		f.write(process_ins(ins))
