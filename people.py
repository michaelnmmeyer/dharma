import os, re, io, unicodedata
import requests
from dharma import config, tree

# Like the eponymous function in xslt
def normalize_space(s):
	s = s.strip()
	return re.sub(r"\s+", " ", s)

"""
To dump a list of all contributors:

for repo in repos/*; do test -d $repo && git -C $repo log --format=%aN; done | sort -u
"""

ID_TO_GIT = {
	"adgu": ["Aditia Gunawan", "aditiagunawan"],
	"adle": ["alevivier"],
	"amwb": ["amandinebricout"],
	"anac": ["andreaacri"],
	"anol": ["Andrew Ollett", "aso2101"],
	"ansc": ["AnneSchmiedchen"],
	"argr": ["Arlo Griffiths", "arlogriffiths"],
	"axja": ["ajaniak", "Axelle Janiak"],
	"chch": ["Chloé", "chloechollet"],
	"cski": ["csabakissgit"],
	"daba": ["danbalogh"],
	"dogo": ["Dominic Goodall", "dg2018"],
	"doso": ["Soutif", "dominiquesoutif"],
	"ekba": ["ekobastiawan"],
	"emfr": ["ManuFrancis", "manufrancis"],
	"emmo": ["emmamorlock"],
	"flde": ["Florinda De Simini", "FlorindaDS"],
	"gibu": ["GiuliaBhu"],
	"ilnu": ["ilhamkang"],
	"jeth": ["jensthomas"],
	"kuch": ["CHHOM Kunthea", "kunthea", "chhomkunthea"],
	"leke": ["leb-ke", "LEB Ke" ],
	"masc": ["Marine", "Marine Schoettel", "marine.schoettel@efeo.net", "m-schoettel"],
	"mime": ["Michaël Meyer", "michaelnmmeyer"],
	"nabo": ["Natasja", "NatasjaSB"],
	"nica": ["NicolasCane"],
	"nimi": ["nmirnig"],
	"nlsy": ["nicholaslua"],
	"nuha": ["nurmaliahabibah"],
	"rozo": ["RobertaGitHub"],
	"ryfu": ["ryosukefurui"],
	"sagu": ["Samana Gururaja", "samana218"],
	"sapi": ["salomepichon"],
	"tilu": ["Tim Lubin", "Tim", "lubint"],
	"tykd": ["tyassanti"],
	"utve": ["UthayaVeluppillai", "Uthaya Veluppillai"],
	"vagi": ["valeriegillet", "Valérie Gillet"],
	"vito": ["Vincent Tournier", "tourniervincent"],
	"wjsa": ["wayanjarrah"],
	"zapa": ["zakariyaaminullah", "Zakariya Pamuji Aminullah"],
}

GIT_TO_ID = {}
for key, values in ID_TO_GIT.items():
	for value in values:
		assert not value in GIT_TO_ID
		GIT_TO_ID[value] = key

ID_TYPES = """
IdHAL
IdRef
ORCID
VIAF
wikidata
""".strip().split()

def load_members_list():
	path = os.path.join(config.REPOS_DIR, "project-documentation/DHARMA_idListMembers_v01.xml")
	xml = tree.parse(path)
	members = {"leke": ["Leb Ke"]} # FIXME
	for person in xml.find("//person"):
		ident = person["xml:id"]
		assert ident not in members
		rec = person.first("persName")
		name = rec.find("name")
		if name:
			assert len(rec.children()) == 1, rec
			name = name[0].text()
			members[ident] = [name]
		else:
			assert len(rec.children()) == 2, rec
			first = rec.first("forename").text()
			last = rec.first("surname").text()
			members[ident] = [last, first]
		for idno in person.find("idno"):
			assert idno["type"] in ID_TYPES
	return members

MEMBERS = load_members_list()

def plain(ident):
	return " ".join(reversed(MEMBERS[ident]))

def plain_from_github(github_user):
	ret = GIT_TO_ID.get(github_user)
	return ret and plain(ret) or github_user

# TODO: normalize, we have both https?:, trailing slash or not, etc.
# https://viaf.org/viaf/66465311
# http://viaf.org/viaf/64048594
def plain_from_viaf(url, dflt=None):
	url = os.path.join(url, "rdf.xml") # easier file to parse
	r = requests.get(url)
	if not r.ok:
		return dflt
	xml = tree.parse(io.StringIO(r.text))
	# choose the most common form of the name hoping it's the most adequate
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
	pass
	"""
	for ident, name in sorted(MEMBERS.items()):
		print(ident, " ".join(name), sep="\t")
"""
