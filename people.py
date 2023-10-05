import os, re, io, unicodedata
from urllib.parse import urlparse
import requests
from dharma import config, tree

SCHEMA = """
begin;

create table if not exists people_main(
	name json check(
		json_array_length(name) between 1 and 2
		and json_type(name -> 0) = 'text'
		and json_array_length(name) = 1 or json_type(name -> 1) = 'text'),
	print_name text as (iif(json_array_length(name) = 1,
		name ->> 0,
		printf('%s %s', name ->> 0, name ->> 1))),
	inverted_name text as (iif(json_array_length(name) = 1,
		name ->> 0,
		printf('%s, %s', name ->> 1, name ->> 0))),
	-- all the following can be null
	dh_id text unique check(dh_id is null or length(dh_id) = 4),
	idhal text unique,
	idref text unique,
	orcid text unique,
	viaf text unique,
	wikidata text unique
);

-- This is filled with git_names.csv. To dump a list of all contributors:
-- for repo in repos/*; do test -d $repo && git -C $repo log --format=%aN; done | sort -u
create table if not exists people_github(
	git_name text primary key not null,
	-- Might be null, not all people on github have a dharma id.
	dh_id text, foreign key(dh_id) references people_main(dh_id)
);

commit;
"""

db = config.open_db("people", SCHEMA)

# Like the eponymous function in xslt
def normalize_space(s):
	s = s.strip()
	return re.sub(r"\s+", " ", s)

ID_TYPES = """
IdHAL
IdRef
ORCID
VIAF
wikidata
""".strip().split()

def normalize_url(url):
	url = url.rstrip("/")
	ret = urlparse(url)
	ret = ret._replace(scheme="https")
	return ret.geturl()
	# could also check that the url works

def iter_members_list():
	path = os.path.join(config.REPOS_DIR, "project-documentation/DHARMA_idListMembers_v01.xml")
	xml = tree.parse(path)
	for person in xml.find("//person"):
		row = {}
		row["dh_id"] = person["xml:id"]
		rec = person.first("persName")
		name = rec.find("name")
		if name:
			assert len(rec.children()) == 1, rec
			row["name"] = [name[0].text()]
		else:
			assert len(rec.children()) == 2, rec
			first = rec.first("forename").text()
			last = rec.first("surname").text()
			row["name"] = [first, last]
		for idno in person.find("idno"):
			typ = idno["type"]
			ltyp = typ.lower()
			assert typ in ID_TYPES
			assert not ltyp in row
			val = idno.text()
			if ltyp != "idhal" and val:
				val = normalize_url(val)
			row[ltyp] = val or None
		for typ in ID_TYPES:
			row.setdefault(typ.lower(), None)
		yield row

@db.transaction
def make_db():
	db.execute("begin")
	for row in iter_members_list():
		db.execute("""
			insert or replace into people_main(name, dh_id, idhal, idref, orcid, viaf, wikidata)
			values(:name, :dh_id, :idhal, :idref, :orcid, :viaf, :wikidata)""", row)
	with open(os.path.join(config.THIS_DIR, "git_names.tsv")) as f:
		seen = set()
		for line_no, line in enumerate(f, 1):
			if line_no == 1:
				continue
			fields = [f.strip() for f in line.split("\t")]
			assert len(fields) == 2, "wrong number of columns at line %d" % line_no
			key, value = fields
			assert key not in seen, "duplicate record %r at line %d" % (key, line_no)
			seen.add(key)
			db.execute("insert or replace into people_github(git_name, dh_id) values(?, ?)", (key, value))
	db.execute("commit")

def plain(ident):
	ret = db.execute("select print_name from people_main where dh_id = ?", (ident,)).fetchone()
	return ret and ret[0] or None

def plain_from_github(github_id):
	ret = db.execute("""select print_name
		from people_main natural join people_github
		where git_name = ?""", (github_id,)).fetchone()
	return ret and ret[0] or github_id

def plain_from_viaf(url, dflt=None):
	# Several formats are available, this one is the easier to parse
	url = os.path.join(url, "rdf.xml")
	r = requests.get(url)
	if not r.ok:
		return dflt
	xml = tree.parse(io.StringIO(r.text))
	# Choose the most common form of the name hoping it's the most adequate
	counts = {}
	for node in xml.find("//prefLabel"):
		text = normalize_space(node.text())
		# try to strip dates at the end as in "Cœdès, George 1886-1969"
		end = len(text)
		while end > 0:
			c = text[end - 1]
			if c.isalpha() or c == ")":
				break
			if c == "." and end >= 3 and text[end - 2].isalpha() and not text[end - 3].isalpha():
				break
			end -= 1
		if end == 0:
			continue
		text = text[:end]
		counts.setdefault(text, 0)
		counts[text] += 1
	names = sorted(counts, key=lambda name: counts[name])
	return names and names.pop() or dflt

if __name__ == "__main__":
	make_db()
