import sys, re
from glob import iglob
from dharma import tree, persons, transform

all = sorted(iglob("texts/DHARMA_*"))
inscriptions = [f for f in all if "DHARMA_INS" in f]
diplomatic = [f for f in all if "DHARMA_DiplEd" in f]
critical = [f for f in all if "DHARMA_CritEd" in f]
critical_edition = [f for f in critical if not "_trans" in f]
critical_translation = [f for f in critical if "_trans" in f]

assert len(inscriptions) + len(diplomatic) \
	+ len(critical_edition) + len(critical_translation) == len(all)

for file in all:
	xml = tree.parse(file)
	langs = set()
	for t in xml.find("//*"):
		if not "lang" in t.attrs:
			continue
		lang = t["lang"]
		if not lang in transform.LANGS:
			print(lang)
