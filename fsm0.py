import sys, re
from glob import iglob
from dharma import tree, people, parse

syms = {}

xml = tree.parse(sys.argv[1])
for define in xml.find("/grammar/define"):
	if define.first("*").name == "element":
		continue
	syms[define["name"]] = define

def print_node(node):
	if node.type == "tag":
		if node.name == "ref":
			define = syms.get(node["name"])
			if not define:
				node["name"] = node["name"].removeprefix("tei_")
				sys.stdout.write(node.xml())
			else:
				for child in define:
					print_node(child)
		elif node.name not in ("pattern", "report", "context", "notAllowed", "ns"):
			if node["a"]:
				del node.attrs["a"]
			sys.stdout.write("<%s" % node.name)
			for k, v in node.attrs.items():
				sys.stdout.write(' %s="%s"' % (k, tree.quote_attribute(v)))
			sys.stdout.write(">")
			for child in node:
				print_node(child)
			sys.stdout.write("</%s>" % node.name)
	else:
		sys.stdout.write(node.xml())

print("<grammar>")
for node in xml.find("/grammar/define/element"):
	if not node["name"]: # start state
		continue
	print_node(node)
print("</grammar>")

sys.exit(0)

files = sorted(iglob("texts/DHARMA_*"))
inscriptions = [f for f in files if "DHARMA_INS" in f]
diplomatic = [f for f in files if "DHARMA_DiplEd" in f]
critical = [f for f in files if "DHARMA_CritEd" in f]
critical_edition = [f for f in critical if not "_trans" in f]
critical_translation = [f for f in critical if "_trans" in f]

assert len(inscriptions) + len(diplomatic) \
	+ len(critical_edition) + len(critical_translation) == len(files)

for file in files:
	xml = tree.parse(file)
	for t in xml.find("//g"):
		x = t["subtype"]
		if x: print(x)
