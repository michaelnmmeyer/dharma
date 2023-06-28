import os, sys, sqlite3
from glob import glob
from bs4 import BeautifulSoup
from dharma.transform import normalize_space
from dharma import config

conn = sqlite3.connect(os.path.join(config.DB_DIR, "ngram.sqlite"))

def normalize(s):
	buf = []
	for c in s:
		if c.isspace():
			buf.append(" ")
		elif c.isalpha():
			buf.append(c.lower())
	return normalize_space("".join(buf))

def index_padas(text):
	ident = os.path.basename(os.path.splitext(text)[0])
	soup = BeautifulSoup(open(text), "xml")
	for verse in soup.find_all("lg"):
		padas = list(verse.find_all("l"))
		if not padas:
			continue
		# XXX in fact <l> sometimes contains several padas, should fix that in the encoding.
		padas = tuple((pada.get("n") or "?", normalize_space(pada.get_text())) for pada in padas)
		id = verse.attrs.get("xml:id") or verse.attrs.get("n")
		if not id:
			id = "?"
		for (n, pada) in padas:
			norm = normalize(pada)
			conn.execute("insert into padas(file, verse, orig, normalized) values(?, ?, ?, ?)",
				(ident, f"{id}.{n}", pada, norm))

def index_verses(text, row):
	ident = os.path.basename(os.path.splitext(text)[0])
	soup = BeautifulSoup(open(text), "xml")
	for verse in soup.find_all("lg"):
		buf = []
		for l in verse.find_all("l"):
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
		print(row,ident, id, norm)
		conn.execute("insert into verses(id, file, verse, orig, normalized) values(?, ?, ?, ?, ?)",
			(row, ident, id, buf, norm))
	return row

def index_all():
	texts = glob("texts/*.xml")
	texts.sort()
	conn.executescript("""
PRAGMA journal_mode = wal;
PRAGMA synchronous = normal;
CREATE TABLE IF NOT EXISTS padas(
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	file TEXT NOT NULL,
	verse TEXT NOT NULL,
	orig TEXT NOT NULL,
	normalized TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS jaccard(
	id1 INTEGER NOT NULL,
	id2 INTEGER NOT NULL,
	coeff REAL,
	PRIMARY KEY(id1, id2)
);
CREATE TABLE IF NOT EXISTS verses(
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	file TEXT NOT NULL,
	verse TEXT NOT NULL,
	orig TEXT NOT NULL,
	normalized TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS verses_jaccard(
	id1 INTEGER NOT NULL,
	id2 INTEGER NOT NULL,
	coeff REAL,
	PRIMARY KEY(id1, id2)
);
""")
	conn.execute("delete from verses")
	conn.execute("delete from verses_jaccard")
	row = 0
	for text in texts:
		row = index_verses(text, row)
	conn.commit()

def iter_all_padas():
	for id, pada in conn.execute("SELECT id, normalized FROM padas"):
		yield (id, pada)

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
			conn.execute("INSERT INTO verses_jaccard VALUES(?, ?, ?)", (id1, id2, jaccard))
	conn.execute("INSERT INTO verses_jaccard SELECT id2, id1, coeff from verses_jaccard")
	conn.commit()

