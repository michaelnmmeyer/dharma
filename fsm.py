import sys
#import openfst_python as fst
#from bs4 import BeautifulSoup

import tree


xml = tree.parse(sys.argv[1])
for node in xml.find("//documentation"):
	node.delete()
"""
for i in range(100):
	for node in xml.find("//choice"):
		for child in node.find("choice"):
			child.unwrap()
print(xml.xml())
"""

for node in xml.find("//element"):
	print(node["name"])
	print("\tattributes")
	for attrib in node.find(".//attribute"):
		print("\t\t%s" % attrib["name"])
	print("\telements")
	for elem in node.find(".//ref"):
		print("\t\t%s" % elem["name"])
	print()
