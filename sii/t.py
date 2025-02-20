from dharma import tree
import sys, re

t = tree.parse(sys.argv[1])

nodes = t.find(".//*")
nodes.sort(key=lambda x: x.location)

for x in nodes:
	if x.name == "ref":
		assert isinstance(x[0], tree.String), x.xml()
		m = re.match(r"((?:[1-9][0-9]*\*?)|\*)[)][ \n]?(.*)", str(x[0]))
		assert m, x.xml()
		bef = x.xml().replace("\n", " ")
		x[0].replace_with(m.group(2))

sys.stdout.write(t.xml())
