import os, sys, unicodedata
from dharma import config, tree

db = config.open_db("texts")

def load_data():
	path = os.path.join(config.REPOS_DIR, "project-documentation", "DHARMA_prosodicPatterns_v01.xml")
	xml = tree.parse(path)
	items = {}
	for item in xml.find("//item"):
		pros = [node for node in item.find(".//seg") if node["type"] == "prosody"]
		assert len(pros) == 1
		pros = pros[0]
		names = set()
		for name in item.find("name") + item.find("label"):
			name = name.text()
			if not name:
				continue
			name = unicodedata.normalize("NFC", name)
			names.add(name)
		for name in names:
			if name in items:
				print(f"duplicate meter: {name}", file=sys.stderr)
				continue
			items[name] = pros.text()
	return items

def make_db():
	data = load_data()
	db.execute("delete from prosody")
	for name, pattern in sorted(data.items()):
		db.execute("insert into prosody(name, pattern) values(?, ?)",
			(name, pattern))

pattern_tbl = str.maketrans({
	"-": "\N{metrical breve}",
	"+": "\N{hyphen-minus}",
	"=": "\N{metrical short over long}",
	"2": "\N{metrical two shorts over long}",
})
def render_pattern(p):
	return "\N{narrow no-break space}".join(p.translate(pattern_tbl))

def is_pattern(p):
	return all(ord(c) in pattern_tbl or c.isdigit() or c in "|/" for c in p)

if __name__ == "__main__":
	for name, pattern in sorted(load_data().items()):
		print(name, pattern, sep="\t")
