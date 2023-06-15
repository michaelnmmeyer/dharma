import os, sys, sqlite3
from glob import glob
from bs4 import BeautifulSoup
from dharma.transform import normalize_space

conn = sqlite3.connect("ngram.sqlite")

def normalize(s):
	buf = []
	for c in s:
		if c.isspace():
			buf.append(" ")
		elif c.isalpha():
			buf.append(c.lower())
	return normalize_space("".join(buf))

def index_text(text):
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

def index_all():
	texts = glob("texts/*.xml")
	texts.sort()
	conn.executescript("""
PRAGMA journal_mode = wal;
DROP TABLE IF EXISTS padas;
CREATE TABLE padas(
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	file TEXT NOT NULL,
	verse TEXT NOT NULL,
	orig TEXT NOT NULL,
	normalized TEXT NOT NULL
);
DROP TABLE IF EXISTS jaccard;
CREATE TABLE jaccard(
	id1 INTEGER NOT NULL,
	id2 INTEGER NOT NULL,
	coeff REAL,
	PRIMARY KEY(id1, id2)
);""")
	for text in texts:
		index_text(text)
	conn.commit()

def iter_all():
	for id, pada in conn.execute("SELECT id, normalized FROM padas"):
		yield (id, pada)

def ngrams(s):
	s = "*" + s + "*"
	return (s[i:i + 3] for i in range(len(s) - 3 + 1))

# index_all()

for id1, pada1 in iter_all():
	ngrams1 = set(ngrams(pada1))
	print(id1)
	for id2, pada2 in iter_all():
		if id1 == id2:
			continue
		ngrams2 = set(ngrams(pada2))
		try:
			jaccard = len(ngrams1 & ngrams2) / len(ngrams1 | ngrams2)
		except ZeroDivisionError:
			jaccard = 0
		conn.execute("INSERT INTO jaccard VALUES(?, ?, ?)", (id1, id2, jaccard))
	conn.commit()

conn.commit()
