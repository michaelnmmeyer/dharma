# import sys, io, html
# from dharma import tree

# syms = {}

# xml = tree.parse(sys.argv[1])
# for define in xml.find("/grammar/define"):
# 	if define.first("*").name == "element":
# 		continue
# 	syms[define["name"]] = define

# def print_node(node, write):
# 	if isinstance(node, tree.Tag):
# 		if node.name == "ref":
# 			define = syms.get(node["name"])
# 			if not define:
# 				node["name"] = node["name"].removeprefix("tei_")
# 				write(node.xml())
# 			else:
# 				for child in define:
# 					print_node(child, write)
# 		elif node.name not in ("pattern", "report", "context", "notAllowed", "ns"):
# 			if node["a"]:
# 				del node.attrs["a"]
# 			write("<%s" % node.name)
# 			for k, v in node.items():
# 				write(' %s=%s' % (k, tree.quote_attribute(v)))
# 			write(">")
# 			for child in node:
# 				print_node(child, write)
# 			write("</%s>" % node.name)
# 	else:
# 		write(node.xml())

# buf = io.StringIO()
# buf.write("<grammar>")
# for node in xml.find("/grammar/define/element"):
# 	if not node["name"]: # start state
# 		continue
# 	print_node(node, buf.write)
# buf.write("</grammar>")
# buf.seek(0)

# xml = tree.parse(buf)
# elements = {}
# for element in xml.find("/grammar/element"):
# 	name = element["name"]
# 	assert name and name not in elements
# 	first = element.first("*")
# 	if first and first.name == "documentation":
# 		doc = first.text()
# 	else:
# 		doc = "undocumented"
# 	attributes = {}
# 	children = set()
# 	parents = set()
# 	elements[name] = {
# 		"documentation": doc,
# 		"attributes": attributes,
# 		"children": children,
# 		"parents": parents,
# 	}
# 	for attribute in element.find(".//attribute"):
# 		name = attribute["name"]
# 		assert name and not name in attributes
# 		first = attribute.first("*")
# 		if first and first.name == "documentation":
# 			doc = first.text()
# 		else:
# 			doc = "undocumented"
# 		attributes[name] = {
# 			"documentation": doc,
# 		}
# 	for ref in element.find(".//ref"):
# 		children.add(ref["name"])

# for element in xml.find("/grammar/element"):
# 	name = element["name"]
# 	for ref in element.find(".//ref"):
# 		elements[ref["name"]]["parents"].add(name)


# print("<html><body>")
# for name, data in sorted(elements.items(), key=lambda x: x[0].lower()):
# 	print("<div>")
# 	print("<h3>")
# 	print(html.escape("<%s>:" % name))
# 	print("</h3>")
# 	print(html.escape(" %s" % data["documentation"]))
# 	print("<h4>Attributes</h4>")
# 	print("<ul>")
# 	for attr, attr_data in sorted(data["attributes"].items()):
# 		print("<li>")
# 		print("<b>")
# 		print(html.escape("@%s" % attr))
# 		print("</b>")
# 		print(html.escape(attr_data["documentation"]))
# 		print("</li>")
# 	print("</ul>")
# 	if data["children"]:
# 		print("<h4>Children</h4>")
# 		print("<b>")
# 		for child in sorted(data["children"]):
# 			print(html.escape("<%s>, " % child))
# 		print("</b>")
# 		print("</div>")
# 	if data["parents"]:
# 		print("<h4>Parents</h4>")
# 		print("<b>")
# 		for child in sorted(data["parents"]):
# 			print(html.escape("<%s>, " % child))
# 		print("</b>")
# 		print("</div>")
# print("</body></html>")
