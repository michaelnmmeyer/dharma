import sys, re
from glob import iglob
from dharma import tree, people, parse

files = sorted(f for f in iglob("texts/DHARMA_*") if not "DHARMA_INSEC" in f)
inscriptions = [f for f in files if "DHARMA_INS" in f]
diplomatic = [f for f in files if "DHARMA_DiplEd" in f]
critical = [f for f in files if "DHARMA_CritEd" in f]
critical_edition = [f for f in critical if not "_trans" in f]
critical_translation = [f for f in critical if "_trans" in f]

assert len(inscriptions) + len(diplomatic) \
	+ len(critical_edition) + len(critical_translation) == len(files)

for file in inscriptions:
	xml = tree.parse(file)
	if '\\' in xml.text():
		print(file)
	continue

	for p in xml.find("//bibl"):

		#print(file,p.path)
		print(p["n"])

		#print(p.xml())
		#print(p.text())
		#if p.children():print(file,p.xml())
		#print(p["type"])
		print(" ".join(t.name for t in p.children()))
		##print(" ".join(t for t in sorted(p.attrs)))


