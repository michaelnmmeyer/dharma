import os
from bs4 import BeautifulSoup
from dharma import config

PATH = os.path.join(config.REPOS_DIR, "project-documentation", "DHARMA_prosodicPatterns_v01.xml")

items = {}

# XXX broken for now, we have several distinct meters that bear the same name;
# is filtering by language sufficient?

soup = BeautifulSoup(open(PATH), "xml")
for item in soup.find_all("item"):
	pros = item.find("seg", type="prosody")
	assert pros, item
	for name in item.find_all("name") + item.find_all("label"):
		name = name.string
		if not name:
			continue
		if name in items:
			assert items[name] == pros.string, name
		items[name] = pros.string

