from dharma import tree
import sys, re, collections

#tadd = tree.parse("sii_add.hid.xml")
tall = tree.parse("sii_all.hid.xml")

tbl = {}
for x in tall.find("//div[@type='insc']"):
	m = re.fullmatch(r"([1-9][0-9]*):([1-9][0-9]*):(.+)", x["n"])
	assert m, x
	vol, page, ins = m.groups()
	tbl.setdefault((vol, ins.rstrip("X")), []).append(x)

for id, items in sorted(tbl.items()):
	if len(items) > 1:
		Y = ""
		for item in items:
			item["n"] = item["n"].rstrip("X") + Y
			Y += "Y"
		#print(items)
	else:
		assert not items[0]["n"].endswith("X")

sys.stdout.write(tall.xml())
