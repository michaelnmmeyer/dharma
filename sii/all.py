import re, sys
from dharma import tree

t = tree.parse("tmp.xml")

old_print = print
def print(*args, **kwargs):
	old_print(*args, **kwargs)
	sys.stdout.flush()

foots = {}

for v in t.find("/doc/div[@type='vol']"):
	cur_vol = int(v["n"].split("-")[0])
	cur_page = 0
	cur_ins = ""
	nodes = v.find(".//*")
	nodes.sort(key=lambda x: x.location)
	for x in nodes:
		if x.name == "pb":
			vol, page = re.fullmatch(r"([1-9][0-9]*):([1-9][0-9]*)", x["n"]).groups()
			vol, page = int(vol), int(page)
			if cur_vol != vol:
				print(x)
			if cur_page > page:
				print(x)
			elif cur_page == 0:
				pass
			else:
				if cur_page + 1 != page:
					print(x)
			cur_page = page
		elif x.name == "div" and x["type"] == "insc":
			assert x["type"] == "insc" and x["n"], x.xml()
			assert len(x.keys()) == 2
			vol, page, ins = re.fullmatch(r"([1-9][0-9]*):([1-9][0-9]*):(.+)", x["n"]).groups()
			vol, page = int(vol), int(page)
			assert cur_vol == vol, x
			assert cur_page > 0, x
			if not cur_page == page:
				print(x)
			cur_ins = ins
		elif x.name == "l":
			assert x["n"] and len(x.keys()) == 1
			vol, page, ins, line = re.fullmatch(r"([1-9][0-9]*):([1-9][0-9]*):([^:]+):(.+)", x["n"]).groups()
			vol, page = int(vol), int(page)
			assert cur_vol == vol, x
			if not cur_page == page:
				print(x)
			if not cur_ins == ins:
				print(x)
		elif x.name == "ref":
			m = re.fullmatch(r"([1-9][0-9]*):([1-9][0-9]*)-(.+)", x["t"])
			if not m:
				print(x)
				continue
			vol, page, foot = m.groups()
			vol, page = int(vol), int(page)
			assert cur_vol == vol, x.xml()
			assert cur_page > 0, x.xml()
			# Disable the following check, because we do have a few
			# footnotes whose contents does not appear on the same
			# page as the footnote mark.
			# assert cur_page == page, x.xml()

#sys.stdout.write(t.xml())
