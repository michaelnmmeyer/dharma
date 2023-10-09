from dharma import tree
import sys

xml = tree.parse(sys.stdin)
for elem in xml.find("//pattern") + xml.find("//documentation"):
	elem.delete()
print(xml.xml())
