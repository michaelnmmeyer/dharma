import os, re, io, unicodedata
import requests # pip install requests
from dharma import config, tree

ID_TYPES = """
IdHAL
IdRef
ORCID
VIAF
wikidata
""".strip().split()

def iter_members_list():
	path = config.path_of("repos/project-documentation/DHARMA_idListMembers_v01.xml")
	xml = tree.parse(path)
	for person in xml.find("//person"):
		row = {}
		row["dh_id"] = person["id"]
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
			# Only keep the last path component:
			# http://viaf.org/viaf/11026260 -> 11026260
			val = val.rsplit("/", 1)[-1]
			row[ltyp] = val or None
		for typ in ID_TYPES:
			row.setdefault(typ.lower(), None)
		affil = rec.first("affiliation")
		if affil:
			affil = affil.text()
		row["affiliation"] = affil or None
		yield row

def make_db():
	db = config.db("texts")
	db.execute("delete from people_github")
	db.execute("delete from people_main")
	for row in iter_members_list():
		db.execute("""
			insert into people_main(name, dh_id, affiliation, idhal, idref, orcid, viaf, wikidata)
			values(:name, :dh_id, :affiliation, :idhal, :idref, :orcid, :viaf, :wikidata)""", row)
	with open(config.path_of("repos/project-documentation/DHARMA_gitNames.tsv")) as f:
		seen = set()
		for line_no, line in enumerate(f, 1):
			if line_no == 1:
				continue
			fields = [f.strip() for f in line.split("\t")]
			assert len(fields) == 2, "wrong number of columns at line %d" % line_no
			key, value = fields
			assert key not in seen, "duplicate record %r at line %d" % (key, line_no)
			seen.add(key)
			db.execute("insert into people_github(git_name, dh_id) values(?, ?)", (key, value))

def plain(ident):
	db = config.db("texts")
	ret = db.execute("select print_name from people_main where dh_id = ?", (ident,)).fetchone()
	return ret and ret[0] or None

def plain_from_github(github_id):
	db = config.db("texts")
	ret = db.execute("""select print_name
		from people_main natural join people_github
		where git_name = ?""", (github_id,)).fetchone()
	return ret and ret[0] or github_id

# XXX use this!
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
		text = config.normalize_space(node.text())
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
