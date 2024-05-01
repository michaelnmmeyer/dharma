from glob import iglob
from dharma import tree

files = sorted(f for f in iglob("texts/DHARMA_INS*") if not "DHARMA_INSEC" in f)
files = sorted(f for f in iglob("texts/DHARMA_DiplEd*"))

for f in files:
	try:
		t = tree.parse(f)
	except tree.Error:
		continue
	for node in t.find("//div"):
		print(f, repr(node))

