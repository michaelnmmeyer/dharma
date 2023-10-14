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

for file in files:
	xml = tree.parse(file)
	for p in xml.find("//milestone"):
		print(p["type"])
		#print(file,p.path)
		#print(p["n"])

		#print(p.xml())
		#print(p.text())
		#if p.children():print(file,p.xml())
		#print(p["type"])
		#print(" ".join(t.name for t in p.children()))
		#print(" ".join(t for t in p.attrs))


