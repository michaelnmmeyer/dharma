from dharma import tree
import re

"""
footnotes (<footnote> or <f>) are supposed to appear after the closing </l>
"""
t = tree.parse("sii_add.xml")

n = "0:0"
nodes = t.find(".//*")
nodes.sort(key=lambda x: x.location)

def to_ints(x):
	a, b = re.match(r"([0-9]+):([0-9]+)", x).groups()
	return int(a.lstrip("0") or "0"), int(b.lstrip("0") or "0")

def num_lt(x, y):
	return to_ints(x) < to_ints(y)

for x in nodes:
	if x.name == "pb":
		assert num_lt(n, x["n"]), f"n={n!r} !< {x['n']!r}"
		n = x["n"]
		#print(x)
	if x.name == "id":
		assert x["n"].startswith(f"{n}:"), x
		#print(x)

for x in t.find("//id"):
	x["l"] = x["n"]
	del x["n"]
for x in t.find("//f"):
 	x.replace_with(" ")

for node in t.find("//h3"):
	parent = node.parent
	i = parent.index(node)
	ins = tree.Tag("div", type="insc")
	ins.append(node)
	while i < len(parent) :
		node = parent[i]
		if isinstance(node, tree.Tag) and node.name == "h3":
			break
		ins.append(node)
	parent.insert(i, ins)

print(t.xml())
