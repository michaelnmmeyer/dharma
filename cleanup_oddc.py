import sys
from dharma import tree

xml = tree.parse(sys.stdin)
for node in xml.find("//exemplum"):
	node.delete()

print(xml.xml())
