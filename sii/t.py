from dharma import tree
import sys, re, collections

tadd = tree.parse("sii_add.hid.xml")
tall = tree.parse("sii_all.hid.xml")

tbl = {}
for x in tall.find("//div[@type='insc']"):
	vol, page, ins = re.fullmatch(r"([1-9][0-9]*):([1-9][0-9]*):(.+)", x["n"]).groups()
	tbl.setdefault((vol, page), []).append(x["n"])

for id, items in tbl.items():
	if len(items) > 1:
		print(items)
