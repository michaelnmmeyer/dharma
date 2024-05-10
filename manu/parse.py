import sys, copy, re, os
from bs4 import BeautifulSoup, Tag, NavigableString
from dharma import tree

soup = BeautifulSoup(sys.stdin, "html.parser")

for name in ("aside", "a", "br", "div"):
	for tag in soup.find_all(name):
		tag.decompose()
for name in ("blockquote",):
	for tag in soup.find_all(name):
		tag.unwrap()
for name in ("p", "em"):
	for tag in soup.find_all("p"):
		if not tag.get_text():
			tag.decompose()
		elif name == "em" and tag.get_text().isspace():
			tag.unwrap()

def fix_em(root, ital=False):
	for child in root:
		if not isinstance(child, Tag):
			if ital:
				child.wrap(soup.new_tag("italic"))
		elif child.name == "em":
			fix_em(child, not ital)
		else:
			fix_em(child, ital)

fix_em(soup)
for tag in soup.find_all("em"):
	tag.unwrap()

for h2 in soup.find_all("h2"):
	del h2["id"]
	for child in h2.find_all(lambda node: isinstance(node, Tag)):
		child.unwrap()
	h2.smooth()
	for child in list(h2.find_all(string=True)):
		child.replace_with(str(child).replace("\n", " "))
	text = h2.get_text()
	match = re.match(r'^Ins\.\s*([0-9]+)\s+(.+)', text)
	assert match
	ins_no, name = match.groups()
	h2["ins_no"] = ins_no.strip()
	h2["ins_name"] = name.strip()
	h2.clear()

for p in soup.find_all("p"):
	for child in list(p.find_all(string=True)):
		child.replace_with(str(child).replace("\n", " "))

soup.smooth()

# grantha
def merge_siblings(name, out_name):
	while True:
		tag = soup.find(name)
		if not tag:
			break
		b = soup.new_tag(out_name)
		b.extend(copy.copy(tag).contents)
		node = tag.next_sibling
		while node is not None:
			if isinstance(node, Tag) and node.name == name:
				next = node.next_sibling
				b.extend(node.extract().contents)
				node = next
			elif not isinstance(node, Tag) and node.isspace() and isinstance(node.next_sibling, Tag) and node.next_sibling.name == name:
				next = node.next_sibling
				b.append(node.extract())
				node = next
			else:
				break
		tag.replace_with(b)

merge_siblings("strong", "b")
merge_siblings("italic", "i")

soup.smooth()

soup2 = BeautifulSoup()

for tag in soup.find_all(lambda node: isinstance(node, Tag) and node.name in ("h2", "p")):
	if tag.name == "h2":
		div = soup2.new_tag("div")
		div.append("\n")
		soup2.append(div)
		soup2.append("\n")
	div.append(copy.copy(tag))
	div.append("\n")

soup = soup2

for div in soup.find_all("div"):
	ps = list(soup.find_all("p"))
	for i, p in enumerate(ps):
		strings = list(p.find_all(string=True))
		if not strings:
			continue
		start = strings[0]
		match = re.match(r"^\[([0-9-]+)\.\]", start)
		if match:
			p["n"] = match.group(1)
			start.replace_with(start[match.end():].lstrip())
		for s in reversed(list(p.find_all(string=True))):
			if not s or s.isspace():
				s.extract()
				continue
			t = s.rstrip()
			if t.endswith("-"):
				if i < len(ps) - 1:
					ps[i + 1]["break"] = "no"
				t = t[:-1]
			elif t.endswith("-/"):
				if i < len(ps) - 1:
					ps[i + 1]["break"] = "no"
				t = t[:-2] + "/"
			s.replace_with(t)
			break

def graphemes(s):
	while s:
		if s.startswith("dh") or s.startswith("th"):
			yield s[:2]
			s = s[2:]
		elif len(s) >= 2 and s[1] == "\N{combining ring below}":
			yield s[:2]
			s = s[2:]
		else:
			yield s[:1]
			s = s[1:]

vowels="aeiouāīū "
def fill(s):
	gs = list(graphemes(s))
	for i, g in enumerate(gs):
		yield g
		if i < len(gs) - 1 and g not in vowels and gs[i + 1] not in vowels:
			yield "="

soup.smooth()
for i in soup.find_all("i"):
	assert i.string
	t = "".join(list(fill(i.get_text())))
	i.replace_with(t)

soup.smooth()
for s in soup.find_all(string=True):
	t = str(s)
	t = t.replace("\N{horizontal ellipsis}", "...")
	o = 0
	while True:
		p = t.find("°", o)
		if p < 0:
			break
		q = o = p + 1
		if t[q] == "[":
			q += 1
		if t[q] in "rh":
			continue
		t = list(t)
		t[p] = ""
		t[q] = t[q].upper()
		t = "".join(t)
	s.replace_with(t)

for s in soup.find_all(string=True):
	s.replace_with(s.replace("\N{light vertical bar}", "|").replace('\xa0', " "))

for s in soup.find_all(string=True):
	orig = s
	tmp = soup.new_tag("foo")
	while True:
		p = s.find("[...]")
		if p < 0:
			break
		tmp.append(s[:p])
		tmp.append(soup.new_tag("gap",
			reason="lost", extent="unknown", unit="character"))
		s = s[p + len("[...]"):]
	tmp.append(str(s))
	orig.replace_with(tmp)
	tmp.unwrap()

for s in soup.find_all(string=True):
	tmp = soup.new_tag("foo")
	start = 0
	for match in re.finditer(r"\[.+?\]", s):
		text = match.group(0)[1:-1]
		if "*" in text:
			continue
		tmp.append(s[start:match.start()])
		unclear = soup.new_tag("unclear")
		unclear.append(text)
		tmp.append(unclear)
		start = match.end()
	tmp.append(str(s[start:]))
	s.replace_with(tmp)
	tmp.unwrap()

for b in soup.find_all("b"):
	l = b.previous_sibling
	r = b.next_sibling
	if not isinstance(l, NavigableString) or not isinstance(r, NavigableString):
		continue
	s = l.rfind("[")
	e = r.find("]")
	if e >= 1 and r[e - 1] == "*":
		continue
	if s < 0 or e < 0:
		continue
	tmp = soup.new_tag("unclear")
	tmp.append(l[s + 1:])
	tmp.append(copy.copy(b))
	tmp.append(r[:e])
	l.replace_with(l[:s])
	r.replace_with(r[e + 1:])
	b.replace_with(tmp)

for b in soup.find_all("b"):
	b.name = "hi"
	b["rend"] = "grantha"
for p in soup.find_all("p"):
	if not "n" in p.attrs:
		p.attrs.clear()
		continue
	p.insert(0, soup.new_tag("lb", **p.attrs))
	p.attrs.clear()
	p.unwrap()
print(soup)

tpl = open("/home/michael/dharma/manu/DHARMA_INSCempiyanMahadevi00001.xml").read()
os.makedirs("out", exist_ok=True)
for div in soup.find_all("div"):
	h2 = div.find("h2").extract()
	t = tree.parse_string(str(div))
	for lb in t.find("//lb"):
		brk = lb["break"]
		del lb["break"]
		lb["break"] = brk
	contents = "".join([node.xml() for node in t.first("//div")]).strip()
	path = "out/DHARMA_INSCempiyanMahadevi%05d.xml" % int(h2["ins_no"])
	ret = tpl.format(ins_no=h2["ins_no"], ins_name=h2["ins_name"], contents=contents,
		ins_no_zpad="%05d" % int(h2["ins_no"]))
	with open(path, "w") as f:
		f.write(ret)
