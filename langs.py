# For ISO 639-3 (languages), the authority is https://iso639-3.sil.org
# For ISO 639-5 (language families), the authority is
# https://www.loc.gov/standards/iso639-5/index.html

import os, unicodedata
import requests # pip install requests
from dharma import config

def fetch_tsv(url):
	if url.startswith("/"):
		with open(url) as f:
			text = f.read()
	else:
		r = requests.get(url)
		r.raise_for_status()
		text = r.text
	lines = text.splitlines()
	fields = lines[0].split("\t")
	ret = []
	for line in lines[1:]:
		row = zip(fields, (x.strip() for x in line.split("\t")))
		ret.append(dict(row))
	return ret

def add_to_index(code, index, rec):
	if not code:
		return
	assert not code in index or index[code] is rec
	index[code] = rec

def load_data():
	tbl3 = fetch_tsv("https://iso639-3.sil.org/sites/iso639-3/files/downloads/iso-639-3.tab")
	tbl3_bis = fetch_tsv("https://iso639-3.sil.org/sites/iso639-3/files/downloads/iso-639-3_Name_Index.tab")
	tbl5 = fetch_tsv("http://id.loc.gov/vocabulary/iso639-5.tsv")
	tbl0 = fetch_tsv(os.path.join(config.REPOS_DIR, "project-documentation/DHARMA_languages.tsv"))
	recs = []
	index = {}
	for row in tbl3:
		rec = {"id": row["Id"], "name": row["Ref_Name"], "iso": 3, "custom": False}
		recs.append(rec)
		# "Part2b", "Part2t", "Part1" are alternate language codes.
		for field in ("Id", "Part2b", "Part2t", "Part1"):
			add_to_index(row[field], index, rec)
	for row in tbl3_bis:
		rec = index[row["Id"]]
		if rec["name"] == row["Print_Name"]:
			assert not rec.get("inverted_name")
			rec["inverted_name"] = row["Inverted_Name"]
	for row in tbl5:
		rec = {
			"id": row["code"],
			"name": row["Label (English)"],
			"inverted_name": row["Label (English)"],
			"iso": 5,
			"custom": False,
		}
		recs.append(rec)
		add_to_index(rec["id"], index, rec)
	for row in tbl0:
		assert not "-" in row["Id"]
		rec = index.get(row["Id"])
		if not rec:
			rec = {
				"id": row["Id"],
				"name": row["Print_Name"],
				"inverted_name": row["Inverted_Name"],
				"iso": None,
				"custom": True,
			}
			recs.append(rec)
			add_to_index(rec["id"], index, rec)
		elif row["Print_Name"] != rec["name"] or row["Inverted_Name"] != rec["inverted_name"]:
			rec["name"] = row["Print_Name"]
			rec["inverted_name"] = row["Inverted_Name"]
			rec["custom"] = True
	assert all("inverted_name" in rec for rec in recs)
	recs.sort(key=lambda rec: rec["id"])
	return recs, index

def normalize_name(s):
	s = unicodedata.normalize("NFKD", s)
	s = "".join(c for c in s if not unicodedata.combining(c))
	s = s.casefold()
	s = s.replace("œ", "oe").replace("æ", "ae").replace("ß", "ss").replace("đ", "d")
	return unicodedata.normalize("NFC", s.strip())

def from_code(s):
	db = config.db("texts")
	(ret,) = db.execute("""select name
		from langs_list natural join langs_by_code
		where code = ?
		""", (s,)).fetchone() or (None,)
	return ret

def make_db():
	db = config.db("texts")
	recs, index = load_data()
	db.execute("delete from langs_by_code")
	db.execute("delete from langs_by_name")
	db.execute("delete from langs_list")
	for rec in recs:
		db.execute("""
			insert into langs_list(id, name, inverted_name, iso, custom)
			values(:id, :name, :inverted_name, :iso, :custom)""", rec)
		db.execute("insert into langs_by_name(id, name) values(?, ?)",
			(rec["id"], normalize_name(rec["name"])))
	for code, rec in sorted(index.items()):
		db.execute("insert into langs_by_code(code, id) values(?, ?)", (code, rec["id"]))
