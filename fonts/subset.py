"""
https://fonttools.readthedocs.io/en/latest/subset

To get script names:

def script(c):
	ret = icu.Script.getScript(c)
	name = ret.getName()
	if name not in ("Common", "Inherited"):
		return name
	ret = icu.Script.getScriptExtensions(c)
	print(ret)
	names = [icu.Script(code).getName() for code in ret]
	return names

[script(c) for c in chars]

Counter([script(c) for c in chars])

https://fonts.googleapis.com/css2?family=Noto+Sans+Mono:wght@300;400;500;600;700&family=Noto+Serif+Grantha&family=Noto+Serif:ital,wght@0,100;0,200;0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,100;1,200;1,300;1,400;1,500;1,600;1,700;1,800;1,900&display=swap

Google uses one file for Latin basic, another for everything else, apparently.
And they use the same font file for all weights viz. they use the
variable-width font files when they are available.

For now we have:

Common
Inherited
Balinese
Cyrillic	['е', 'н', 'о', 'ә']
Devanagari
Grantha
Greek
Gujarati
Han
Kannada
Khmer
Latin
Oriya
Tamil
Telugu

See if its better to work with blocks instead of scripts. Probably is for the Latin stuff at least

>>> print("\n".join(sorted(set([subset.block_of(c) for c in chars]))))
Arrows
Balinese
Basic Latin
CJK Symbols and Punctuation
CJK Unified Ideographs
Combining Diacritical Marks
Cyrillic
Devanagari
Dingbats
General Punctuation
Geometric Shapes
Grantha
Greek Extended
Greek and Coptic
Gujarati
Halfwidth and Fullwidth Forms
IPA Extensions
Kannada
Khmer
Latin Extended Additional
Latin Extended-A
Latin Extended-B
Latin-1 Supplement
Letterlike Symbols
Mathematical Operators
Miscellaneous Mathematical Symbols-A
Miscellaneous Mathematical Symbols-B
Miscellaneous Symbols
Miscellaneous Technical
Number Forms
Oriya
Spacing Modifier Letters
Superscripts and Subscripts
Supplemental Punctuation
Tamil
Telugu





Deal separately with "Common" and "Inherited". See if we can subsume them within ScriptExtensions.
Also should include just the schwa in Cyrillic, for Andrea (unless sth else is actually used!).

Also add the relevant option to pyftsubset to make it check that we have all needed characters:
--no-ignore-missing-unicodes


data = open("../all_texts.txt").read()
chars = set(data)
for c in chars.copy():
	if c.isspace() or c in "\N{bom}\N{zwsp}\N{soft hyphen}":
		chars.remove(c)

"""

import sys

blocks_to_keep = set("""
Arrows
Balinese
Basic Latin
CJK Symbols and Punctuation
CJK Unified Ideographs
Combining Diacritical Marks
Cyrillic
Devanagari
Dingbats
General Punctuation
Geometric Shapes
Grantha
Greek Extended
Greek and Coptic
Gujarati
Halfwidth and Fullwidth Forms
IPA Extensions
Kannada
Khmer
Latin Extended Additional
Latin Extended-A
Latin Extended-B
Latin-1 Supplement
Letterlike Symbols
Mathematical Operators
Miscellaneous Mathematical Symbols-A
Miscellaneous Mathematical Symbols-B
Miscellaneous Symbols
Miscellaneous Technical
Number Forms
Oriya
Spacing Modifier Letters
Superscripts and Subscripts
Supplemental Punctuation
Tamil
Telugu
""".strip().splitlines())

# https://codecolibri.fr/optimiser-ses-polices-web-avec-le-font-subsetting/

def iter_lines(f):
	for line in f:
		end = line.find('#')
		if end >= 0:
			line = line[:end]
		line = line.strip()
		if line:
			yield line

def scan_lines(f):
	for line in iter_lines(f):
		first, second = tuple(f.strip() for f in line.split(';'))
		if ".." in first:
			start, end = first.split("..")
			start = int(start, 16)
			end = int(end, 16)
		else:
			start = first
			start = int(start, 16)
			end = start
		name = second
		yield (start, end + 1), name

def make_set():
	chars = set()
	f = open("Scripts.txt")
	for (start, end), script in scan_lines(f):
		if not script in scripts_to_keep:
			continue
		for char in range(start, end):
			chars.add(char)
	return chars

def load_blocks():
	ret = {}
	with open("Blocks.txt") as f:
		for (start, end), name in scan_lines(f):
			if not name in blocks_to_keep:
				continue
			for c in range(start, end):
				#print("U+%04X" % c, name)
				ret[c] = name
	return ret

BLOCKS = load_blocks()

def block_of(c):
	return BLOCKS.get(ord(c))

chars = BLOCKS
for char in sorted(chars):
	print("U+%04X" % char)

"""
pyftsubset $f --unicodes-file=unicodes.txt --flavor=woff2 --harfbuzz-repacker --output-file=`notext $f`-subset.woff2
"""
