import sys
from dharma import tree

def fix_choice_order(xml):
	for node in xml.find("//choice"):
		children = node.children()
		if len(children) != 2:
			continue
		l, r = children
		if l.name == "corr" and r.name == "sic" or l.name == "reg" and r.name == "orig":
			pass
		else:
			continue
		i, j = node.index(l), node.index(r)
		node[i], node[j] = node[j], node[i]

def fix_g(xml):
	for g in xml.find("//g"):
		if g["type"] == "symbol" and g["subtype"]:
			g["type"] = g["subtype"]
			del g["subtype"]

t = tree.parse(sys.stdin)
fix_g(t)
sys.stdout.write(tree.xml(t))
