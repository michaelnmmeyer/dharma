import os, sys, icu, unicodedata
from collections import Counter

def graphemes(s):
	itor = icu.BreakIterator.createCharacterInstance(icu.Locale()) 
	itor.setText(s)
	p = 0
	for q in itor:
		yield s[p:q]
		p = q

def all_graphemes():
	for line in sys.stdin:
		yield from graphemes(line)

gs = Counter(all_graphemes())
for g, count in gs.items():
	if len(g) == 1:
		continue
	print(repr(g), count)
