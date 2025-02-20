from dharma import tree
import sys

t = tree.parse(sys.argv[1])

for div in t.find("//div[@type='insc']"):
	id = div.first("stuck-child::id[@h]")
	assert id
	div["n"] = id["h"]
	id.delete()

for l in t.find("//l"):
	id = l.first("stuck-preceding-sibling::id[@l]")
	assert id, l.xml()
	l["n"] = id["l"]
	id.delete()


sys.stdout.write(t.xml())
