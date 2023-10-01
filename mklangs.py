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

tbl3 = fetch_tsv("https://iso639-3.sil.org/sites/iso639-3/files/downloads/iso-639-3.tab")
tbl3_bis = fetch_tsv("https://iso639-3.sil.org/sites/iso639-3/files/downloads/iso-639-3_Name_Index.tab")
tbl5 = fetch_tsv("http://id.loc.gov/vocabulary/iso639-5.tsv")

recs = []
index = {}

def add_to_index(code, rec):
	if not code:
		return
	assert not code in index or index[code] is rec
	index[code] = rec

for row in tbl3:
	rec = {"id": row["Id"], "name": row["Ref_Name"], "iso": 3}
	recs.append(rec)
	for field in ("Id", "Part2B", "Part2T", "Part1"):
		add_to_index(row[field], rec)

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
	add_to_index(rec["id"], rec)

assert all("inverted_name" in rec for rec in recs)

recs.sort(key=lambda rec: rec["id"])

def normalize_name(s):
	s = unicodedata.normalize("NFKD", s)
	s = "".join(c for c in s if not unicodedata.combining(c))
	s = s.casefold()
	s = s.replace("œ", "oe").replace("æ", "ae").replace("ß", "ss").replace("đ", "d")
	return unicodedata.normalize("NFC", s.strip())

SCHEMA = """
begin;
create table if not exists list(
	id text primary key check(length(id) = 3),
	name text,
	inverted_name text,
	iso integer check(iso = 3 or iso = 5)
);
create table if not exists by_code(
	code text primary key check(length(code) >= 2 and length(code) <= 3),
	id text, foreign key(id) references list(id)
);
create virtual table if not exists by_name using fts5(
	id unindexed, -- text primary key, foreign key(id) references list(id)
	name,
	tokenize = "trigram"
);
commit;
"""

db = config.open_db("langs", SCHEMA)

@db.transaction
def make_db():
	db.execute("begin")
	db.execute("delete from by_code")
	db.execute("delete from by_name")
	db.execute("delete from list")
	for rec in recs:
		db.execute("insert into list(id, name, inverted_name, iso) values(:id, :name, :inverted_name, :iso)", rec)
		db.execute("insert into by_name(id, name) values(?, ?)", (rec["id"], normalize_name(rec["name"])))
	for code, rec in sorted(index.items()):
		db.execute("insert into by_code(code, id) values(?, ?)", (code, rec["id"]))
	db.execute("commit")
	db.execute("vacuum")

if __name__ == "__main__":
	make_db()
