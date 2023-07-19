import sys, re
from bs4 import BeautifulSoup
from glob import iglob
from dharma.transform import normalize_space

all = sorted(iglob("texts/DHARMA_*"))
inscriptions = [f for f in all if "DHARMA_INS" in f]
diplomatic = [f for f in all if "DHARMA_DiplEd" in f]
critical = [f for f in all if "DHARMA_CritEd" in f]
critical_edition = [f for f in critical if not "_trans" in f]
critical_translation = [f for f in critical if "_trans" in f]

assert len(inscriptions) + len(diplomatic) \
	+ len(critical_edition) + len(critical_translation) == len(all)

def process_lg(lg):
	for choice in lg.find_all("choice"):
		if choice.corr:
			choice.replace_with(choice.corr.get_text())
		elif choice.reg:
			choice.replace_with(choice.reg.get_text())
	for space in lg.find_all("space"):
		space.replace_with(" ")
	for name in ("rdg", "note", "milestone", "pb", "lb", "gap", "del", "label"):
		for tag in lg.find_all(name):
			tag.decompose()
	for l in lg.find_all("l"):
		print(l.get("n"))
		#print(l.attrs, normalize_space(l.get_text()))

for file in all:
	soup = BeautifulSoup(open(file), "xml")
	for lg in soup.find_all("lg"):
		process_lg(lg)
