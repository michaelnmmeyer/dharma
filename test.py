from glob import iglob
import sys
from dharma import tree, langs

files = sorted(f for f in iglob("texts/DHARMA_INS*") if not "DHARMA_INSEC" in f)

for f in files:
	try:
		t = tree.parse(f)
	except tree.Error:
		continue
	for node in t.find("//prefixDef[@ident]"):
		print(node["ident"])
