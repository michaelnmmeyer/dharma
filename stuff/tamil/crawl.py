import io, os, sys, re, sqlite3, time, requests
from bs4 import BeautifulSoup

dicts = "fabricius kadirvelu mcalpin tamil-idioms tamil-lex winslow".split()

db = sqlite3.connect("tamil.sqlite.tmp")
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
		db.execute("insert into raw_pages(url, when_downloaded, data) values(?, strftime('%s', 'now'), ?)",
			(url, r.text))
		if page % 50 == 0:
			db.commit()
		if not "Next Page" in r.text:
			break
		time.sleep(5)
	db.commit()

def download_all():
	for name in dicts:
		if name == "crea": # broken next page links, see with Manu
			continue
		download_dict(name)

def page_from_url(url):
	return int(url.rsplit("=", 1)[1])

def dict_from_url(url):
	return re.search(r"/([^/]+)_query\.py", url).group(1)

db.create_function("page_from_url", 1, page_from_url, deterministic=True)
db.create_function("dict_from_url", 1, dict_from_url, deterministic=True)

# the HTML is broken, so we have to do this
def iter_entries_in_page(data):
	in_entry = False
	buf = []
	for line in data.splitlines():
		line = line.strip()
		if line == "<div>&nbsp;&nbsp;":
			assert not in_entry
			in_entry = True
			buf.clear()
			buf.append(line)
			continue
		if line == "</div>":
			if not in_entry:
				continue
			in_entry = False
			buf.append(line)
			yield " ".join(buf)
			continue
		buf.append(line)
	assert not in_entry

def iter_entries(dict_name):
	for dict, page, data in db.execute("""
		select dict_from_url(url) as dict, page_from_url(url) as page, data
		from raw_pages
		where url glob ? order by page""", ("*%s_query*" % dict_name,)):
		for entry in iter_entries_in_page(data):
			yield dict, page, entry

for row in iter_entries("*"):
	print(*row, sep="\t")
