# For ISO 639-3 (languages), the authority is https://iso639-3.sil.org
# For ISO 639-5 (language families), the authority is
# https://www.loc.gov/standards/iso639-5/index.html

import requests, unicodedata
from dharma import config

def fetch_tsv(url):
	r = requests.get(url)
	r.raise_for_status()
	lines = r.text.splitlines()
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
	recs = []
	index = {}
	for row in tbl3:
		rec = {"id": row["Id"], "name": row["Ref_Name"], "iso": 3}
		recs.append(rec)
		for field in ("Id", "Part2B", "Part2T", "Part1"):
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
		}
		recs.append(rec)
		add_to_index(rec["id"], index, rec)
	assert all("inverted_name" in rec for rec in recs)
	recs.sort(key=lambda rec: rec["id"])
	return recs, index

def normalize_name(s):
	s = unicodedata.normalize("NFKD", s)
	s = "".join(c for c in s if not unicodedata.combining(c))
	s = s.casefold()
	s = s.replace("œ", "oe").replace("æ", "ae").replace("ß", "ss").replace("đ", "d")
	return unicodedata.normalize("NFC", s.strip())

db = config.open_db("texts")

@db.transaction
def make_db():
	recs, index = load_data()
	db.execute("begin")
	db.execute("delete from langs_by_code")
	db.execute("delete from langs_by_name")
	db.execute("delete from langs_list")
	for rec in recs:
		db.execute("insert into langs_list(id, name, inverted_name, iso) values(:id, :name, :inverted_name, :iso)", rec)
		db.execute("insert into langs_by_name(id, name) values(?, ?)", (rec["id"], normalize_name(rec["name"])))
	for code, rec in sorted(index.items()):
		db.execute("insert into langs_by_code(code, id) values(?, ?)", (code, rec["id"]))
	db.execute("commit")

if __name__ == "__main__":
	make_db()
