import os, sys, unicodedata, re
from bs4 import BeautifulSoup, Comment, NavigableString, Tag

def normalize_space(s):
	s = s.strip()
	return re.sub(r"\s+", " ", s)

def normalize(s):
	buf = []
	for c in s:
		if c.isspace():
			buf.append(" ")
		elif c.isalpha():
			buf.append(c.lower())
		elif c == "’" or c == "'":
			buf.append("a")
	return normalize_space("".join(buf))

verses = []

soup = BeautifulSoup(sys.stdin, "xml")
for verse in soup.find_all("lg"):
	buf = []
	for i, l in enumerate(verse.find_all("l")):
		# In fact <l> sometimes contains several padas, should fix that in the encoding.
		n = l.get("n", "").replace(" ", "").replace("-", "")
		assert n in "abcdefgh"
		for tag in ("rdg", "note"):
			for x in l.find_all(tag):
				x.decompose()
		for tag in ("app", "lem", "sic", "witDetail"):
			for x in l.find_all(tag):
				x.unwrap()
		l.smooth()
		assert l.string, l
		text = l.string
		text = text.replace(",", "")
		text = normalize_space(text.strip())
		text = text.strip("/| ")
		buf.append(text)
		if "abcdefgh"[i] != n:
			print(verse["n"])
	if not buf:
		continue
	if not any(c.isalpha() for c in " ".join(buf)):
		continue
	id = verse["n"]
	verses.append((id, tuple(buf), tuple(normalize(pada) for pada in buf)))

DATA = verses

def ngrams(s):
	s = "*" + s + "*"
	return (s[i:i + 3] for i in range(len(s) - 3 + 1))

MIN_JACCARD = 0.2

def make_jaccard(itor):
	data = list(itor)
	jac = []
	for id1, (_, _, chunk1) in enumerate(data):
		ngrams1 = set(ngrams(chunk1))
		for id2, (_, _, chunk2) in enumerate(data):
			if id1 >= id2:
				continue
			ngrams2 = set(ngrams(chunk2))
			try:
				jaccard = len(ngrams1 & ngrams2) / len(ngrams1 | ngrams2)
			except ZeroDivisionError:
				jaccard = 0
			if jaccard <= MIN_JACCARD:
				continue
			jac.append((id1, id2, jaccard))
	ret = []
	for i1, i2, jaccard in jac:
		id1, text1, _ = data[i1]
		id2, text2, _ = data[i2]
		rec = (jaccard, id1, text1, id2, text2)
		ret.append(rec)
	ret.sort(reverse=True)
	return ret

def iter_verses():
	for id, text, norm in DATA:
		if len(text) >= 4:
			vid = id if len(text) == 4 else id + "abcd"
			vtext = "%s %s | %s %s ||" % text[:4]
			vnorm = " ".join(norm[:4])
			yield vid, vtext, vnorm
		if len(text) >= 8:
			vid = id + "efgh"
			vtext = "%s %s | %s %s ||" % text[4:]
			vnorm = " ".join(norm[4:])
			yield vid, vtext, vnorm

def iter_hemistiches():
	for id, text, norm in DATA:
		for i in range(0, len(text) // 2 * 2, 2):
			hid = id + "abcdefgh"[i:i + 2]
			htext = "%s %s %s" % (text[i], text[i + 1], i % 4 and "|" or "||")
			hnorm = " ".join(norm[i:i + 2])
			yield hid, htext, hnorm

def iter_padas():
	for id, text, norm in DATA:
		for i, p in enumerate("abcdefgh"):
			if i >= len(text):
				break
			yield id + p, text[i], norm[i]

units = [
	("verses", iter_verses),
	("hemistiches", iter_hemistiches),
	("padas", iter_padas),
]

for name, itor in units:
	with open("%s.csv" % name, "w") as f:
		ret = make_jaccard(itor())
		for x in ret:
			print(*x, file=f, sep=",")
