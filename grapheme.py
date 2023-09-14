import os, sys, icu, unicodedata, html
from dharma import texts, cleanup

def graphemes(s):
	# ICU returns UTF-16 offsets, but we're working at the code point-level.
	itor = icu.BreakIterator.createCharacterInstance(icu.Locale())
	itor.setText(s)
	p, q, p16 = 0, 0, 0
	for q16 in itor:
		while p16 < q16:
			if ord(s[q]) > 0xffff:
				p16 += 1
				assert p16 < q16
			p16 += 1
			q += 1
		yield s[p:q]
		p = q

def char_name(c):
	try:
		return unicodedata.name(c)
	except ValueError:
		return "U+%04X" % ord(c)

SCRIPTS = ("TAMIL", "TELUGU", "KHMER", "DEVANAGARI", "GRANTHA", "KANNADA", "BALINESE")

def script(g):
	# Not really correct, but enough for this purpose
	names = [char_name(c) for c in g]
	for s in SCRIPTS:
		if all(name.startswith(s + " ") for name in names):
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
	if len(g) == 1:
		if g[0] == "\N{CYRILLIC SMALL LETTER SCHWA}":
			return True
		return not char_name(g[0]).startswith("CYRILLIC ")
	return script(g) or g in valid_combinations

def validate(f):
	problems = []
	for line_no, line in enumerate(f, 1):
		line = unicodedata.normalize("NFC", line.rstrip())
		gs = list(graphemes(line))
		for i, g in enumerate(gs):
			if is_valid(g):
				continue
			hl = html.escape("".join(gs[:i]))
			hl += "<mark>%s</mark>" % html.escape(g)
			hl += html.escape("".join(gs[i + 1:]))
			names = [char_name(c) for c in g]
			problem = {
				"line_no": line_no,
				"highlighted_line": hl,
				"grapheme": names,
			}
			problems.append(problem)
	return problems

def validate_repo(name):
	ret = {}
	for file in texts.iter_texts_in_repo(name):
		with open(file) as f:
			problems = validate(f)
		ret[file] = problems
	return ret

if __name__ == "__main__":
	for line in sys.stdin:
		p = 0
		for g in graphemes(line):
			names = [char_name(c) for c in g]
			print(p, names)
			p += len(g)
