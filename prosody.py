import os, sys
from bs4 import BeautifulSoup
from dharma import config

PATH = os.path.join(config.REPOS_DIR, "project-documentation", "DHARMA_prosodicPatterns_v01.xml")

items = {}

soup = BeautifulSoup(open(PATH), "xml")
for item in soup.find_all("item"):
	pros = item.find("seg", type="prosody")
	assert pros, item
	names = set()
	for name in item.find_all("name") + item.find_all("label"):
		name = name.string
		if not name:
			continue
		names.add(name)
	for name in names:
		if name in items:
			print(f"duplicate meter: {name}", file=sys.stderr)
			continue
		items[name] = pros.string

