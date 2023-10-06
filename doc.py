import sys, re, io
from dharma import tree, people, parse

syms = {}

xml = tree.parse(sys.argv[1])
for define in xml.find("/grammar/define"):
	if define.first("*").name == "element":
		continue
	syms[define["name"]] = define

def print_node(node, write):
	if node.type == "tag":
		if node.name == "ref":
			define = syms.get(node["name"])
			if not define:
				node["name"] = node["name"].removeprefix("tei_")
				write(node.xml())
			else:
				for child in define:
					print_node(child, write)
		elif node.name not in ("pattern", "report", "context", "notAllowed", "ns"):
			if node["a"]:
				del node.attrs["a"]
			write("<%s" % node.name)
			for k, v in node.attrs.items():
				write(' %s="%s"' % (k, tree.quote_attribute(v)))
			write(">")
			for child in node:
				print_node(child, write)
			write("</%s>" % node.name)
	else:
		write(node.xml())

buf = io.StringIO()
buf.write("<grammar>")
for node in xml.find("/grammar/define/element"):
	if not node["name"]: # start state
		continue
	print_node(node, buf.write)
buf.write("</grammar>")
buf.seek(0)

xml = tree.parse(buf)
elements = {}
for element in xml.find("/grammar/element"):
	name = element["name"]
	assert name and name not in elements
	first = element.first("*")
	if first and first.name == "documentation":
		doc = first.text()
	else:
		doc = "undocumented"
	attributes = {}
	children = set()
	elements[name] = {
		"documentation": doc,
		"attributes": attributes,
		"children": children,
	}
	for attribute in element.find(".//attribute"):
		name = attribute["name"]
		assert name and not name in attributes
		first = attribute.first("*")
		if first and first.name == "documentation":
			doc = first.text()
		else:
			doc = "undocumented"
		attributes[name] = {
			"documentation": doc,
		}
	for ref in element.find(".//ref"):
		children.add(ref["name"])

for name, data in sorted(elements.items()):
	print("<%s> %s" % (name, data["documentation"]))
	for attr, attr_data in sorted(data["attributes"].items()):
		print("\t@%s %s" % (attr, attr_data["documentation"]))
