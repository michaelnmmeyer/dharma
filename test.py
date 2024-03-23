import sys, re
from glob import iglob
from dharma import tree, people, parse

files = sorted(f for f in iglob("texts/DHARMA_INS*") if not "DHARMA_INSEC" in f)

for file in files:
	xml = tree.parse(file)
	for p in xml.find("//persName"):
		print(p["ref"])
