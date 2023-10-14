import sys
from dharma import tree

xml = tree.parse(sys.stdin, keep_namespaces=True)

for name in ("listRef", "exemplum", "remarks", "context", "constraintSpec"):
	for elem in xml.find("//" + name):
		elem.delete()

print(xml.xml())
