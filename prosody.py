import os, sys
from dharma import config, tree

PATH = os.path.join(config.REPOS_DIR, "project-documentation", "DHARMA_prosodicPatterns_v01.xml")

items = {}

xml = tree.parse(PATH)
for item in xml.find("//item"):
	pros = [node for node in item.find(".//seg") if node.get("type") == "prosody"]
	assert len(pros) == 1
	pros = pros[0]
	names = set()
	for name in item.find("name") + item.find("label"):
		name = name.text()
		if not name:
			continue
		names.add(name)
	for name in names:
		if name in items:
			#print(f"duplicate meter: {name}", file=sys.stderr)
			continue
		items[name] = pros.text()
