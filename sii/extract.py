from dharma import tree

t = tree.parse("sii_all.xml")

for ins in t.find("//div[@type='insc']"):
	loc = ins.first("stuck-child::id[@h]")
	assert loc
