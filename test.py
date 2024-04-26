from glob import iglob
from dharma import tree

files = sorted(f for f in iglob("texts/DHARMA_INS*") if not "DHARMA_INSEC" in f)

for f in files:
	t = tree.parse(f)
	for node in t.find("//*[@n and glob('*-*', @n)]"):
		div = node.first("""ancestor::div[@type='edition' or @type='translation'
			or @type='commentary' or @type='bibliography']""")
		parent = div and div["type"] or "?"
		print(parent, node.name, node["n"])

