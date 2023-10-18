import os, sys, sqlite3, time, requests

dicts = "crea fabricius kadirvelu mcalpin tamil-idioms tamil-lex winslow".split()

db = sqlite3.connect("tamil.sqlite")
db.executescript("""
pragma page_size = 16384;
pragma journal_mode = wal;
pragma synchronous = normal;
pragma foreign_keys = on;
pragma secure_delete = off;

create table if not exists raw_pages(
	url text primary key,
	when_downloaded timestamp,
	data text
);
""")

def download_dict(name):
	page = 0
	while True:
		page += 1
		url = f"https://dsal.uchicago.edu/cgi-bin/app/{name}_query.py?page={page}"
		print(url)
		r = requests.get(url)
		r.raise_for_status()
		r.encoding = "UTF-8"
		# Can't rely on the "Next page" links, they are a mess.
		if "Please click to next page for content" in r.text:
			break
		db.execute("insert into raw_pages(url, when_downloaded, data) values(?, strftime('%s', 'now'), ?)",
			(url, r.text))
		if page % 50 == 0:
			db.commit()
		time.sleep(2)
	db.commit()

for name in dicts:
	download_dict(name)
