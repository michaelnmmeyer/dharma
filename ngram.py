import os, sys, string, unicodedata, re, html
from glob import glob
from bs4 import BeautifulSoup
from dharma.transform import normalize_space
from dharma import config, texts

SCHEMA = """
create table if not exists data(
	type integer, -- 1 = verse, 2 = hemistich, 4 = pada
	id integer,
	file text,
	number text,
	contents html,
	normalized text,
	primary key(type, id)
);
create table if not exists jaccard(
	type integer,
	id integer,
	id2 integer,
	coeff real,
	primary key(type, id, id2),
	foreign key(type, id) references data(type, id),
	foreign key(type, id2) references data(type, id)
);
"""

NGRAMS_DB = config.open_db("ngrams")
NGRAMS_DB.executescript(SCHEMA)
NGRAMS_DB.commit()

translit_tbl = [
	("r\N{COMBINING RING BELOW}", "ṛ"),
	("r\N{COMBINING RING BELOW}\N{COMBINING MACRON}", "ṝ"),
	("l\N{COMBINING RING BELOW}", "ḷ"),
	("l\N{COMBINING RING BELOW}\N{COMBINING MACRON}", "ḹ"),
	("ṁ", "ṃ"),
	("m\N{COMBINING CANDRABINDU}", "ṃ"), 
]

def normalize(s):
	buf = []
	s = s.lower()
	for k, v in translit_tbl:
		s = s.replace(k, v)
	for c in s:
		if c.isspace():
			buf.append(" ")
		elif c.isalpha() or unicodedata.combining(c) > 0:
			buf.append(c)
		elif c == "’":
			buf.append("a")
	ret = normalize_space("".join(buf))
	return ret

def cleanup(s):
	buf = []
	s = unicodedata.normalize("NFC", s)
	# hack
	s = re.sub(r"\[\d+.*?\]", "", s)
	s = s.replace("[]", "")
	s = s.replace("\N{CYRILLIC SMALL LETTER SCHWA}", "\N{LATIN SMALL LETTER SCHWA}")
	s = s.replace("_", " ")
	s = re.sub(r'[◉◆“”.+\\,|/"॥।*!]', "", s)
	# end hack
	for c in s:
		if c.isspace():
			c = " "
		elif c in "’'ʼ":
			c = "’"
		buf.append(c)
	ret = normalize_space("".join(buf))
	return ret

def extract_pada(l):
	for choice in l.find_all("choice"):
		if choice.corr:
			choice.replace_with(choice.corr.get_text())
		elif choice.reg:
			choice.replace_with(choice.reg.get_text())
	for space in l.find_all("space"):
		space.replace_with(" ")
	for name in ("rdg", "note", "milestone", "pb", "lb", "gap", "del", "label"):
		for tag in l.find_all(name):
			tag.decompose()
	text = cleanup(l.get_text())
	if l.get("enjamb") == "yes" and not text.startswith("-"):
		text = "-" + text
	return text

def extract_padas(lg):
	ret = []
	letters = "".join(l.get("n", "X") for l in lg.find_all("l"))
	if letters != string.ascii_lowercase[:len(letters)]:
		return ret
	for l in lg.find_all("l"):
		ret.append(extract_pada(l))
	if not any(c.isalpha() for pada in ret for c in pada):
		ret.clear()
	return ret

def number_of(verse):
	n = verse.get("n")
	if not n:
		return "?"
	node = verse
	while True:
		node = node.parent
		while node and node.name != "div":
			node = node.parent
		if not node:
			break
		pn = node.get("n")
		if pn:
			n = pn + "." + n
	return n

def extract_verses(path):
	soup = BeautifulSoup(open(path), "xml")
	for verse in soup.find_all("lg"):
		padas = extract_padas(verse)
		if not padas:
			continue
		n = number_of(verse)
		yield n, padas

def trigrams(s):
	return (s[i:i + 3] for i in range(len(s) - 3 + 1))

MIN_JACCARD = 0.3

def enum_verses(n, orig, norm):
	for i in range(0, len(orig) // 4 * 4, 4):
		vn = n
		if len(orig) > 4:
			vn += string.ascii_lowercase[i:i + 4]
		vorig = '<div class="verse"><p>%s %s |</p><p>%s %s ||</p></div>' % \
			tuple(html.escape(p) for p in orig[i:i + 4])
		vnorm = "*%s %s**%s %s*" % tuple(norm[i:i + 4])
		yield vn, vorig, vnorm

def enum_hemistiches(n, orig, norm):
	for i in range(0, len(orig) // 2 * 2, 2):
		vn = n + string.ascii_lowercase[i:i + 2]
		if (i + 2) % 4 == 0:
			end = "||"
		else:
			end = "|"
		vorig = '<div class="verse"><p>%s %s ' % tuple(html.escape(p) for p in orig[i:i + 2]) + \
			'%s</p></div>' % end
		vnorm = "*%s %s*" % tuple(norm[i:i + 2])
		yield vn, vorig, vnorm

def enum_padas(n, orig, norm):
	for i in range(len(orig)):
		vn = n + string.ascii_lowercase[i]
		vorig = '<div class="verse"><p>%s</p></div>' % orig[i]
		vnorm = "*%s*" % norm[i]
		yield vn, vorig, vnorm

enum_funcs = [
	(1, enum_verses),
	(2, enum_hemistiches),
	(4, enum_padas),
]

def process_files(paths):
	id = 0
	for path in paths:
		path = path.strip()
		file = os.path.basename(os.path.splitext(path)[0])
		for n, orig in extract_verses(path):
			norm = [normalize(pada) for pada in orig]
			for type, func in enum_funcs:
				for number, contents, normalized in func(n, orig, norm):
					id += 1
					yield type, id, file, number, contents, normalized

def make_jaccard(type):
	data = []
	for id, normalized in NGRAMS_DB.execute("select id, normalized from data where type=?", (type,)):
		data.append((id, set(trigrams(normalized))))
	for i, (id1, ngrams1) in enumerate(data):
		print("%d %d/%d" % (type, i, len(data)))
		for id2, ngrams2 in data:
			if id1 >= id2:
				continue
			try:
				jaccard = len(ngrams1 & ngrams2) / len(ngrams1 | ngrams2)
			except ZeroDivisionError:
				jaccard = 0
			if jaccard < MIN_JACCARD:
				continue
			NGRAMS_DB.execute("insert into jaccard values(?, ?, ?, ?)", (type, id1, id2, jaccard))

if __name__ == "__main__":
	db = NGRAMS_DB
	db.execute("begin")
	for row in process_files(texts.iter_texts()):
		db.execute("insert into data values(?, ?, ?, ?, ?, ?)", row)
	db.execute("commit")
	for type, _ in enum_funcs:
		db.execute("begin")
		make_jaccard(type)
		db.execute("commit")
