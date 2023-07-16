import os, sys
from glob import glob
from bs4 import BeautifulSoup
from dharma.transform import normalize_space
from dharma import config

SCHEMA = """
create table if not exists verses(
	id integer primary key autoincrement,
	file text not null,
	verse text not null,
	orig text not null,
	normalized text not null
);
create table if not exists verses_jaccard(
	id1 integer,
	id2 integer,
	coeff real,
	primary key(id1, id2),
	foreign key(id1) references verses(id),
	foreign key(id2) references verses(id)
);
"""

NGRAM_DB = config.open_db("ngram")
NGRAM_DB.executescript(SCHEMA)
NGRAM_DB.commit()

def normalize(s):
	buf = []
	for c in s:
		if c.isspace():
			buf.append(" ")
		elif c.isalpha():
			buf.append(c.lower())
	return normalize_space("".join(buf))

def index_verses(text, row):
	ident = os.path.basename(os.path.splitext(text)[0])
	soup = BeautifulSoup(open(text), "xml")
	for verse in soup.find_all("lg"):
		buf = []
		for l in verse.find_all("l"):
			# In fact <l> sometimes contains several padas, should fix that in the encoding.
			n = l.get("n", "").replace(" ", "").replace("-", "")
			if not n in ("a", "b", "c", "d", "ab", "cd"):
				buf.clear()
				break
			text = normalize_space(l.get_text().strip())
			text = text.strip("/| ")
			buf.append(text)
			if n.endswith("b"):
				buf.append("|\n")
			elif n.endswith("d"):
				buf.append("||")
		if not buf:
			continue
		buf = " ".join(buf)
		if not any(c.isalpha() for c in buf):
			continue
		id = verse.attrs.get("xml:id") or verse.attrs.get("n") or "?"
		norm = normalize(buf)
		row += 1
		print(row, ident, id, norm)
		conn.execute("insert into verses(id, file, verse, orig, normalized) values(?, ?, ?, ?, ?)",
			(row, ident, id, buf, norm))
	return row

def index_all():
	texts = glob("texts/*.xml")
	texts.sort()
	conn.execute("delete from verses")
	conn.execute("delete from verses_jaccard")
	row = 0
	for text in texts:
		row = index_verses(text, row)
	conn.commit()

def iter_all_verses():
	for id, verse in conn.execute("select id, normalized from verses"):
		yield (id, verse)

def ngrams(s):
	s = "*" + s + "*"
	return (s[i:i + 3] for i in range(len(s) - 3 + 1))

def precompute():
	start = conn.execute("select max(id1) from verses_jaccard").fetchone()[0] or 0
	for id1, chunk1 in iter_all_verses():
		if id1 <= start:
			continue
		ngrams1 = set(ngrams(chunk1))
		print(id1)
		for id2, chunk2 in iter_all_verses():
			if id1 >= id2:
				continue
			ngrams2 = set(ngrams(chunk2))
			try:
				jaccard = len(ngrams1 & ngrams2) / len(ngrams1 | ngrams2)
			except ZeroDivisionError:
				jaccard = 0
			if jaccard <= 0.3:
				continue
			conn.execute("insert into verses_jaccard values(?, ?, ?)", (id1, id2, jaccard))
	conn.execute("insert into verses_jaccard select id2, id1, coeff from verses_jaccard")
	conn.commit()
