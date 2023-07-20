import os, sys, string, unicodedata, re, html
from glob import glob
from bs4 import BeautifulSoup
from dharma.transform import normalize_space
from dharma import config, texts

SCHEMA = """
create table if not exists sources(
	file text primary key,
	verses integer,
	hemistiches integer,
	padas integer
);
create table if not exists passages(
	type integer, -- 1 = verse, 2 = hemistich, 4 = pada
	id integer,
	file text,
	number text,
	contents html,
	normalized text,
	parallels integer,
	primary key(type, id),
	foreign key(file) references sources(file)
);
create table if not exists jaccard(
	type integer,
	id integer,
	id2 integer,
	coeff real,
	primary key(type, id, id2),
	foreign key(type, id) references passages(type, id),
	foreign key(type, id2) references passages(type, id)
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

def process_file(path, id):
	file = os.path.basename(os.path.splitext(path)[0])
	for n, orig in extract_verses(path):
		norm = [normalize(pada) for pada in orig]
		for type, func in enum_funcs:
			for number, contents, normalized in func(n, orig, norm):
				id += 1
				yield type, id, file, number, contents, normalized

def make_jaccard(type):
	data = []
	for id, normalized in NGRAMS_DB.execute("select id, normalized from passages where type = ?", (type,)):
		data.append((id, set(trigrams(normalized))))
	for i, (id1, ngrams1) in enumerate(data, 1):
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

def make_database():
	db = NGRAMS_DB
	db.execute("begin")
	id = 0
	for path in texts.iter_texts():
		file = os.path.basename(os.path.splitext(path)[0])
		db.execute("insert into sources(file) values(?)", (file,))
		for row in process_file(path, id):
			db.execute("""insert into passages(type, id, file, number, contents, normalized)
				values(?, ?, ?, ?, ?, ?)""", row)
			id = row[1]
	db.execute("commit")
	for type, _ in enum_funcs:
		db.execute("begin")
		make_jaccard(type)
		db.execute("commit")
	db.executescript("""
	begin;
	insert into jaccard select type, id2, id, coeff from jaccard;
	update passages set parallels = (select count(*) from jaccard
		where jaccard.type = passages.type and jaccard.id = passages.id);
	update sources set
		verses = (select count(*) from passages where passages.file = sources.file and type = 1 and parallels > 0),
		hemistiches = (select count(*) from passages where passages.file = sources.file and type = 2 and parallels > 0),
		padas = (select count(*) from passages where passages.file = sources.file and type = 4 and parallels > 0);
	commit;
	vacuum;
	""")

def search(src_text, category):
	if category == "verse":
		danda = re.search(r"[/|।]", src_text)
		if not danda:
			return None, None
		one, two = src_text[:r.end()], src_text[r.end():]
		src_norm = "*%s**%s*" % (normalize(cleanup(one)), normalize(cleanup(two)))
		formatted_text = '<div class="verse"><p>%s</p><p>%s</p></div>' % \
			html.escape(one), html.escape(two)
		type = 1
	elif category == "hemistich" or category == "pada":
		src_norm = "*%s*" % normalize(cleanup(src_text))
		formatted_text = '<div class="verse"><p>%s</p></div>' % html.escape(src_text)
		type = category == "hemistich" and 2 or 4
	else:
		return None, None
	src_ngrams = set(trigrams(src_norm))
	ret = []
	for row in NGRAMS_DB.execute("""
		select id, normalized, file, number, contents from passages where type = ?
		""", (type,)):
		ngrams2 = set(trigrams(row["normalized"]))
		try:
			jaccard = len(src_ngrams & ngrams2) / len(src_ngrams | ngrams2)
		except ZeroDivisionError:
			jaccard = 0
		if jaccard < MIN_JACCARD:
			continue
		ret.append((row["id"], row["file"], row["number"], row["contents"], jaccard))
	ret.sort(key=lambda x: x[-1], reverse=True)
	return ret, formatted_text
