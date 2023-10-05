import sys, re
from glob import iglob
from dharma import tree, people, parse

files = sorted(iglob("texts/DHARMA_*"))
inscriptions = [f for f in files if "DHARMA_INS" in f]
diplomatic = [f for f in files if "DHARMA_DiplEd" in f]
critical = [f for f in files if "DHARMA_CritEd" in f]
critical_edition = [f for f in critical if not "_trans" in f]
critical_translation = [f for f in critical if "_trans" in f]

assert len(inscriptions) + len(diplomatic) \
	+ len(critical_edition) + len(critical_translation) == len(files)

for file in inscriptions:
	xml = tree.parse(file)
	for t in xml.find("//variantEncoding"):
		for k, v in sorted(t.attrs.items()):
			print(k)
