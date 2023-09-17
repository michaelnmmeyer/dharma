import sys, re
from bs4 import BeautifulSoup
from glob import iglob
from dharma import tree, persons
from dharma.transform import normalize_space

all = sorted(iglob("texts/DHARMA_*"))
inscriptions = [f for f in all if "DHARMA_INS" in f]
diplomatic = [f for f in all if "DHARMA_DiplEd" in f]
critical = [f for f in all if "DHARMA_CritEd" in f]
critical_edition = [f for f in critical if not "_trans" in f]
critical_translation = [f for f in critical if "_trans" in f]

assert len(inscriptions) + len(diplomatic) \
	+ len(critical_edition) + len(critical_translation) == len(all)

urls = set()
for file in all:
	xml = tree.parse(file)
	for pers in xml.find("//persName"):
		ref = pers.get("ref", "")
		if ref.startswith("http"):
			urls.add(ref)

for url in urls:
	print(url, persons.plain_from_viaf(url))

