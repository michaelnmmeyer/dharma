import sys, re
from glob import iglob
from dharma import tree

files = sorted(f for f in iglob("texts/DHARMA_INS*") if not "DHARMA_INSEC" in f)

attrs = "corresp break met style rend enjamb rendition lang place url resp real id".split()

def print_all_nums(root, n, buf=""):
	if root.name in ("bibl", "ref", "graphic", "rs", "table", "fw"):
		return
	if root["n"]:
		for attr in attrs:
			del root[attr]
		buf += root["n"]
		print(n * "\t" + buf + " " + repr(root))
		n += 1
		buf += '$'
	for elem in root.children():
		print_all_nums(elem, n, buf)

"""
default for milestones is gridlike (i think)

<pb>
	<lb>

<lb>
	<milestone unit="column">

pagelike = {"faces"}
gridlike

pagelike


gridlike
– "block"
– "column"
– "face"
– "fragment"
– "zone"















"""
def print_phys_nums(root, n, buf):
	if root["n"] and root.name in ("pb", "lb", "milestone"):
		for attr in attrs:
			del root[attr]
		buf += root["n"]
		print(n * "\t" + repr(root))
		n += 1
		buf += '$'
	for elem in root.children():
		print_phys_nums(elem, n, buf)

for file in files:
	#print(file)
	xml = tree.parse(file)
	edition = xml.first("//div")
	assert edition["type"] == "edition"
	elems = set()
	for elem in edition.find("//lg"):
		print(elem["met"])
