tbl = {


	0x8c: "ā",
	0xb4: "ī",
	0xe8: "ū",
	0xa8: "ṛ",
	0xa5: "ṝ",
	# ḷ
	# ḹ
	0xb5: "ṃ",
	0xfa: "ḥ",

	0xba: "ṅ",

	0x96: "ñ",

	0xa0: "ṭ",
	0xb6: "ḍ",
	0xdf: "Ḍ",
	0xf6: "ṇ",

	0xa7: "ś",
	0xb7: "ṣ",

	0xea: "Ś",
	0xdd: "Ṣ",

	0xd5: "’",
	0xee: "Ā",
	0x9c: "u",
}

import sys
data = open(sys.argv[1], "rb").read()
for c in data:
	if c > 127:
		if not c in tbl and c != 0xc2:
			#print(sys.argv[1], "%02x" % c)
			pass
		c = tbl.get(c, "<0x%02x>" % c)
	else:
		c = chr(c)
		if c == '\r': c = '\n'
	sys.stdout.write(c)

"""
./Subhasitasamgraha.txt 9f
./Subhasitasamgraha.txt 95
./Subhasitasamgraha.txt 9c
./Subhasitasamgraha.txt a1

c2
"""
