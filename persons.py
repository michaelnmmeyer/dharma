#!/usr/bin/env python3

import os, io, unicodedata
from bs4 import BeautifulSoup, Tag
from dharma.transform import normalize_space

"""
To dump a list of all contributors:

	for repo in repos/*; do
		test -d $repo || continue;
		git -C $repo log --format='%aN'
	done | sort -u
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

this_dir = os.path.dirname(os.path.abspath(__file__))
path = "repos/project-documentation/DHARMA_idListMembers_v01.xml"
path = os.path.join(this_dir, path)

with open(path) as f:
	text = unicodedata.normalize("NFC", f.read())
	soup = BeautifulSoup(io.StringIO(text), "xml")

def count_children_tags(iter):
	n = 0
	for x in iter:
		if isinstance(x, Tag):
			n += 1
	return n

persons = {"leke": ["Leb", "Ke"]}

for person in soup.find_all("person"):
	ident = person["xml:id"].strip()
	rec = person.persName
	name = rec.find("name")
	assert ident not in persons
	if name:
		assert count_children_tags(rec.children) == 1, rec
		name = normalize_space(name.get_text())
		persons[ident] = [name]
	else:
		assert count_children_tags(rec.children) == 2, rec
		first = normalize_space(rec.forename.get_text())
		last = normalize_space(rec.surname.get_text())
		persons[ident] = [first, last]

def plain(ident):
	return " ".join(persons[ident])

def plain_from_github(github_user):
	return plain(GIT_TO_ID[github_user])

def xml(ident, root_tag):
	rec = persons[ident]
	soup = BeautifulSoup(f"<{root_tag}></{root_tag}>", "xml")
	root = soup.find(root_tag)
	root["ref"] = "part:%s" % ident
	if len(rec) == 1:
		name = soup.new_tag("name")
		name.string = rec[0]
		root.append(name)
	else:
		first = soup.new_tag("forename")
		first.string = rec[0]
		last = soup.new_tag("surname")
		last.string = rec[1]
		root.append(first)
		root.append(last)
	return root

if __name__ == "__main__":
	for ident, name in sorted(persons.items()):
		print(ident, " ".join(name), sep="\t")
