import sys
from dharma import tree, cleanup

def fix_choice_order(xml):
	for node in xml.find("//choice"):
		children = node.children()
		if len(children) != 2:
			continue
		l, r = children
		if l.name == "corr" and r.name == "sic" or l.name == "reg" and r.name == "orig":
			pass
		else:
			continue
		i, j = node.index(l), node.index(r)
		node[i], node[j] = node[j], node[i]

def fix_g(xml):
	for g in xml.find("//g"):
		if g["type"] == "symbol" and g["subtype"]:
			g["type"] = g["subtype"]
			del g["subtype"]
	# <g>|</g> -> <g type="danda">.</g>
	# <g>||</g> -> <g type="danda">.</g>
	for g in xml.find("//g"):
		if g["type"] or g["subtype"]:
			continue
		if len(g) > 1 or not g[0].type == "string":
			continue
		if g[0] in ("|", "।"):
			g["type"] = "danda"

		elif g[0] in ("||", "॥"):
			g["type"] = "ddanda"
		else:
			continue
		g[0].replace_with(".")

def fix_change_when(xml):
	for change in xml.find("//revisionDesc/change"):
		when = change["when"]
		if when.isdigit() and len(when) == 4: # if a year
			change["when"] = f"{when}-01-01"

def fix_tags_decl(xml):
	for node in xml.find("//tagsDecl"):
		node.delete()

# TODO
# * Use form A for responsibilities https://github.com/erc-dharma/project-documentation/issues/242
# * add a fix for ṃ, ṛ, ṝ, ḹ (_and_ also in the rendering code) if Arlo confirms at
# https://github.com/erc-dharma/project-documentation/issues/251

# TODO for manu https://github.com/erc-dharma/project-documentation/issues/197#issuecomment-1883341358
# PS: I think you have somewhere a list of automatic changes to be implemented on the DHARMA files; maybe add to this list the change of <hi rend="grantha"> to the correct encoding <seg rend="grantha" rendition="class:38768 maturity:83213"> in <div type="edition"> as well as in <div type="apparatus">, as I might still use <hi rend="grantha"> as a short-hand encoding.

document = sys.stdin.read()
document = cleanup.normalize_string(document)
t = tree.parse_string(document)
for key, value in globals().copy().items():
	if key.startswith("fix_"):
		print(key, file=sys.stderr)
		value(t)

sys.stdout.write(tree.xml(t))
