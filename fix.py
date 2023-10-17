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
