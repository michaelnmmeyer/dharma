from dharma import tree
import sys, re, collections

tall = tree.parse("sii_all.hid.xml")
tadd = tree.parse("sii_add.hid.xml")

tall_data = {}
for x in tall.find("//div[@type='insc']"):
	id = x["n"]
	tall_data[id] = x

adds = tadd.find("//div[@type='insc']")
start = tadd.first("//div[@type='insc' and @n='4:206:673']")
assert start is not None
i = 0
while i < len(adds):
	if adds[i] is start:
		break
	i += 1
assert i < len(adds)

for add in adds:#[i:]:
	id = add["n"]
	all = tall_data[id]
	assert len(all.find("h3")) == 1, id
	assert len(add.find("h3")) <= 1, id
	all.first("h3").delete()
	# all_h4 = all.find("h4")
	# add_h4 = add.find("h4")
	# if all_h4 and len(all_h4) != len(add.find("h4")):
	# 	print(id)
	# 	continue
	# if all_h4:
	# 	l4 = "".join(x.text().strip() for x in all_h4)
	# 	d4 = "".join(x.text().strip() for x in add_h4)
	# 	if l4 != d4: print(id)
	# continue
	for tag in ("tlka", "h4", "TL", "pb"):
		for node in all.find(tag):
			node.delete()
	for elem in add:
		all.append(elem.copy())
	# if not all.empty:
	# 	print(id, "notempty")

sys.stdout.write(tall.xml())
