import os, sys, icu, unicodedata, html

def graphemes(s):
	itor = icu.BreakIterator.createCharacterInstance(icu.Locale())
	itor.setText(s)
	p = 0
	for q in itor:
		yield s[p:q]
		p = q

def char_name(c):
	try:
		return unicodedata.name(c)
	except ValueError:
		return "U+%04X" % ord(c)

def script(g):
	# Not really correct, but enough for this purpose
	names = [char_name(c) for c in g]
	for s in ("TAMIL", "TELUGU", "KHMER", "DEVANAGARI", "GRANTHA"):
		if all(name.startswith(s) for name in names):
			return s

valid_combinations = """
\N{LATIN SMALL LETTER R}\N{COMBINING RING BELOW}
\N{LATIN CAPITAL LETTER L}\N{COMBINING RING BELOW}
\N{LATIN CAPITAL LETTER R}\N{COMBINING RING BELOW}
\N{LATIN SMALL LETTER M}\N{COMBINING TILDE}
\N{LATIN SMALL LETTER SCHWA}\N{COMBINING MACRON}
\N{LATIN SMALL LETTER L}\N{COMBINING RING BELOW}
\N{LATIN SMALL LETTER M}\N{COMBINING CANDRABINDU}
\N{LATIN SMALL LETTER R}\N{COMBINING RING BELOW}\N{COMBINING MACRON}
\N{LATIN CAPITAL LETTER L}\N{COMBINING RING BELOW}\N{COMBINING MACRON}
\N{LATIN CAPITAL LETTER R}\N{COMBINING RING BELOW}\N{COMBINING MACRON}
\N{LATIN SMALL LETTER L}\N{COMBINING RING BELOW}\N{COMBINING MACRON}
\N{LATIN SMALL LETTER N}\N{COMBINING BREVE}
""".strip().splitlines()

def is_valid(g):
	return len(g) == 1 or script(g) or g in valid_combinations

def find_problems(f):
	problems = {}
	lines = {}
	for line_no, line in enumerate(f, 1):
		line = unicodedata.normalize("NFC", line.rstrip())
		hl = ""
		ok = True
		for g in graphemes(line):
			eg = html.escape(g)
			if is_valid(g):
				hl += eg
				continue
			hl += "<mark>%s</mark>" % eg
			names = [char_name(c) for c in g]
			problems.setdefault(line_no, []).append(names)
			ok = False
		if not ok:
			lines[line_no] = "<p>%s</p>" % hl
	for line_no, line in sorted(lines.items()):
		print(line)		

for name in sys.argv[1:]:
	with open(name) as f:
		find_problems(f)
