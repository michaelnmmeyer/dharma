import sys, re
from glob import iglob
from dharma import tree, persons, parse

all = sorted(iglob("texts/DHARMA_*"))
inscriptions = [f for f in all if "DHARMA_INS" in f]
diplomatic = [f for f in all if "DHARMA_DiplEd" in f]
critical = [f for f in all if "DHARMA_CritEd" in f]
critical_edition = [f for f in critical if not "_trans" in f]
critical_translation = [f for f in critical if "_trans" in f]

assert len(inscriptions) + len(diplomatic) \
	+ len(critical_edition) + len(critical_translation) == len(all)

for file in inscriptions:
	xml = tree.parse(file)
	for t in xml.find("//gap"):
		r = t["unit"]
		if r not in "lost illegible undefined ellipsis omitted".split():
			print(r)

