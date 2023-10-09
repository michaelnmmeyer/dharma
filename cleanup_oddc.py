import sys
from dharma import tree

xml = tree.parse(sys.stdin)

for name in ("listRef", "exemplum", "remarks", "context", "constraintSpec"):
	for elem in xml.find("//" + name):
		elem.delete()

print(xml.xml())
