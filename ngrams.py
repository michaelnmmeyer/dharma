import os, sys, string, unicodedata, re, html
from glob import glob
from dharma import config, texts, tree

# TODO try multisets: https://en.wikipedia.org/wiki/Jaccard_index
# better results? makes sense?

# TODO highlight clusters that differ from the source (or the contrary)

SCHEMA = """
begin;
create table if not exists metadata(
	key text primary key,
	value blob
);
insert or ignore into metadata values('last_updated', 0);

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
commit;
"""

NGRAMS_DB = config.open_db("ngrams", SCHEMA)

translit_tbl = [
	("r\N{COMBINING RING BELOW}", "ṛ"),
	("r\N{COMBINING RING BELOW}\N{COMBINING MACRON}", "ṝ"),
	("l\N{COMBINING RING BELOW}", "ḷ"),
	("l\N{COMBINING RING BELOW}\N{COMBINING MACRON}", "ḹ"),
	("ṁ", "ṃ"),
	("m\N{COMBINING CANDRABINDU}", "ṃ"),
]
translit_tbl.sort(key=lambda x: len(x[0]), reverse=True)

def normalize(s):
	buf = []
	s = s.lower()
	for k, v in translit_tbl:
		s = s.replace(k, v)
	for c in s:
		if c == "-":
			continue
		elif c.isspace() or c.isalpha() or unicodedata.combining(c) > 0:
			buf.append(c)
		elif c == "’":
			buf.append("a")
	ret = "".join(buf)
	return ret.strip()

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
	ret = config.normalize_space("".join(buf))
	return ret

def extract_pada(l):
	for choice in l.find(".//choice"):
		corr = choice.first("corr") or choice.first("reg")
		if corr:
			corr.replace_with(corr.text())
	for space in l.find(".//space"):
		space.replace_with(" ")
	for name in ("rdg", "note", "milestone", "pb", "lb", "gap", "del", "label"):
		for tag in l.find(f".//{name}"):
			tag.delete()
	text = cleanup(l.text())
	if l["enjamb"] == "yes" and not text.startswith("-"):
		text = "-" + text
	return text

def extract_padas(lg):
	ret = []
	letters = "".join(l["n"] or "X" for l in lg.find("l"))
	if letters != string.ascii_lowercase[:len(letters)]:
		return ret
	for l in lg.find("l"):
		ret.append(extract_pada(l))
	if not any(c.isalpha() for pada in ret for c in pada):
		ret.clear()
	return ret

def number_of(verse):
	n = verse["n"] or "?"
	node = verse
	while True:
		node = node.parent
		while node and node.name != "div":
			node = node.parent
		if not node:
			break
		pn = node["n"]
		if pn:
			n = pn + "." + n
	return n

def extract_verses(path):
	xml = tree.parse(path)
	for verse in xml.find("//lg"):
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
		vorig = '<div class="parallel-verse"><p>%s %s |</p><p>%s %s ||</p></div>' % \
			tuple(html.escape(p) for p in orig[i:i + 4])
		vnorm = " %s %s %s %s " % tuple(norm[i:i + 4])
		yield vn, vorig, re.sub(r"\s{2,}", " ", vnorm)

def enum_hemistiches(n, orig, norm):
	for i in range(0, len(orig) // 2 * 2, 2):
		vn = n + string.ascii_lowercase[i:i + 2]
		if (i + 2) % 4 == 0:
			end = "||"
		else:
			end = "|"
		vorig = '<div class="parallel-verse"><p>%s %s ' % tuple(html.escape(p) for p in orig[i:i + 2]) + \
			'%s</p></div>' % end
		vnorm = " %s %s " % tuple(norm[i:i + 2])
		yield vn, vorig, re.sub(r"\s{2,}", " ", vnorm)

def enum_padas(n, orig, norm):
	for i in range(len(orig)):
		vn = n + string.ascii_lowercase[i]
		vorig = '<div class="parallel-verse"><p>%s</p></div>' % orig[i]
		vnorm = " %s " % norm[i]
		yield vn, vorig, re.sub(r"\s{2,}", " ", vnorm)

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

def make_jaccard(type, db):
	data = []
	for id, normalized in db.execute("select id, normalized from passages where type = ?", (type,)):
		data.append((id, set(trigrams(normalized))))
	for i, (id1, ngrams1) in enumerate(data, 1):
		print("%d %d/%d" % (type, i, len(data)))
		for id2, ngrams2 in data:
			if id1 >= id2:
				continue
			try:
				inter = len(ngrams1 & ngrams2)
				jaccard = inter / (len(ngrams1) + len(ngrams2) - inter)
			except ZeroDivisionError:
				jaccard = 0
			if jaccard < MIN_JACCARD:
				continue
			db.execute("insert into jaccard values(?, ?, ?, ?)", (type, id1, id2, jaccard))

@NGRAMS_DB.transaction
def make_database():
	db = NGRAMS_DB
	db.execute("begin")
	for tbl in ("jaccard", "passages", "sources"):
		db.execute(f"delete from {tbl}")
	id = 0
	for path in texts.iter_texts():
		file = os.path.basename(os.path.splitext(path)[0])
		db.execute("insert into sources(file) values(?)", (file,))
		for row in process_file(path, id):
			db.execute("""insert into passages(type, id, file, number, contents, normalized)
				values(?, ?, ?, ?, ?, ?)""", row)
			id = row[1]
	for type, _ in enum_funcs:
		make_jaccard(type, db)
	db.execute("insert into jaccard select type, id2, id, coeff from jaccard")
	db.execute("""update passages set parallels = (select count(*) from jaccard
		where jaccard.type = passages.type and jaccard.id = passages.id)""")
	db.execute("""update sources set
		verses = (select count(*) from passages where passages.file = sources.file and type = 1 and parallels > 0),
		hemistiches = (select count(*) from passages where passages.file = sources.file and type = 2 and parallels > 0),
		padas = (select count(*) from passages where passages.file = sources.file and type = 4 and parallels > 0)
	""")
	db.execute("insert or replace into metadata values('last_updated', strftime('%s', 'now'))")
	db.execute("commit")
	db.execute("vacuum")

def jaccard(s1, s2):
	ngrams1 = set(trigrams(s1))
	ngrams2 = set(trigrams(s2))
	try:
		inter = len(ngrams1 & ngrams2)
		return inter / (len(ngrams1) + len(ngrams2) - inter)
	except ZeroDivisionError:
		return 0

NGRAMS_DB.create_function("jaccard", 2, jaccard, deterministic=True)

PER_PAGE = 50

@NGRAMS_DB.transaction
def search(src_text, category, page):
	if category == "verse":
		danda = re.search(r"[/|।]", src_text)
		if not danda:
			danda = re.search("$", src_text)
		one, two = src_text[:danda.end()], src_text[danda.end():]
		src_norm = " %s %s " % (normalize(cleanup(one)), normalize(cleanup(two)))
		formatted_text = '<div class="parallel-verse"><p>%s</p><p>%s</p></div>' % \
			(html.escape(one), html.escape(two))
		type = 1
	elif category == "hemistich" or category == "pada":
		src_norm = " %s " % normalize(cleanup(src_text))
		formatted_text = '<div class="parallel-verse"><p>%s</p></div>' % html.escape(src_text)
		type = category == "hemistich" and 2 or 4
	else:
		return None, None, 0, PER_PAGE, 0
	src_norm = re.sub(r"\s{2,}", " ", src_norm)
	offset = (page - 1) * PER_PAGE
	limit = PER_PAGE + 1
	db = NGRAMS_DB
	db.execute("begin")
	# XXX don't do writes here, find another solution
	db.execute("""
		create temp table parallels_search_results(
			id integer primary key,
			coeff real
		)
	""")
	db.execute("""
		insert into parallels_search_results
		select id, jaccard(?, normalized) as coeff
		from passages where type = ? and coeff > 0""",
		(src_norm, type))
	(total,) = db.execute("select count(*) from parallels_search_results").fetchone()
	ret = db.execute("""
		select id, file, number, contents, coeff
		from parallels_search_results natural join passages
		order by coeff desc
		limit ? offset ?""", (limit, offset)).fetchall()
	db.execute("drop table parallels_search_results")
	db.execute("commit")
	return ret, formatted_text, page, PER_PAGE, total

if __name__ == "__main__":
	make_database()
