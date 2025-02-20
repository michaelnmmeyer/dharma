"""
Have id/@h for {volume}:{page}:{inscription_no}
Have id/@l for {volume}:{page}:{inscription_no}:{line_no}
Have pb/@n for {volume}:{page}

ref is used for footnotes:

	<ref t="4:2-1">The inscription is only a
	fragment.</ref>

	@t="4:2-1" means vol. 4 p. 2 fn. 1.

page numbers in id/@l are typically incorrect.
"""

import re
from dharma import tree

t = tree.parse("sii_all.hid.xml")

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
			assert cur_vol == vol, x.xml()
			assert cur_page < page
			if cur_page == 0:
				pass
			else:
				assert cur_page + 1 == page, x.xml()
			cur_page = page
		elif x.name == "id":
			assert len(x.keys()) == 1
			if x["h"]:
				vol, page, ins = re.fullmatch(r"([1-9][0-9]*):([1-9][0-9]*):(.+)", x["h"]).groups()
				vol, page = int(vol), int(page)
				assert cur_vol == vol, x.xml()
				assert cur_page > 0, x.xml()
				assert cur_page == page
				cur_ins = ins
				#print(x["h"])
			else:
				vol, page, ins, line = re.fullmatch(r"([1-9][0-9]*):([1-9][0-9]*):([^:]+):(.+)", x["l"]).groups()
				vol, page = int(vol), int(page)
				assert cur_vol == vol, x.xml()
				assert cur_page > 0, x.xml()
				assert cur_page == page
				assert cur_ins
				#XXX reenable assert cur_ins == ins, x.xml()
		elif x.name == "ref":
			vol, page, foot = re.fullmatch(r"([1-9][0-9]*):([1-9][0-9]*)-(.+)", x["t"]).groups()
			vol, page = int(vol), int(page)
			assert cur_vol == vol, x.xml()
			assert cur_page > 0, x.xml()
			# Disable the following check, because we do have a few
			# footnotes whose contents does not appear on the same
			# page as the footnote mark.
			# assert cur_page == page, x.xml()
			if not x["type"] == "repeated": foots.setdefault(x["t"], []).append(x)


for foot, vals in sorted(foots.items()):
	if len(vals) == 1:
		continue
	prev = None
	for val in vals:
		if prev is None:
			prev = val
			assert not prev["type"]
			continue
		if prev.xml().replace("\n", " ") == val.xml().replace("\n", " "):
			val.clear()
			val["type"] = "repeated"
			continue
		prev = val

open("out.xml", "w").write(t.xml())
