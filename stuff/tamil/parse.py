import os, sys, io, sqlite3, unicodedata
from bs4 import BeautifulSoup, NavigableString, Comment, Tag
import translit
from xml.etree import ElementTree as ET

"""

<tam>
	wraps text in tamil, whatever the location

<hw>, <hw1>
	holds the entry headword; for tamil-idioms, we have:
	<hw1>aṭittuppōṭṭāṟ pōl</hw1> <b>அடித்துப்போட்டாற் போல்</b>

<t>
	holds transliterated text of the headword (only of it?)

<pos>
	for lexical information (gender,...); can be unwrapped
	if not in italics already

<b>
	sometimes only marker for headwords

<smallcaps>
	holds text in caps, lowerize it and format with small caps

<p2>
	?

For tamil-idioms, we also have, after the entry body (still within the div):

	<blockquote><small>1 பொ. வி. 1</small></blockquote>

"""

def trim_space(entry):
	i = 0
	while i < len(entry.contents):
		node = entry.contents[i]
		if not isinstance(node, NavigableString):
			break
		if node.isspace():
			node.replace_with("")
			i += 1
		else:
			node.replace_with(node.lstrip())
			break
	i = len(entry.contents)
	while i > 0:
		i -= 1
		node = entry.contents[i]
		if not isinstance(node, NavigableString):
			break
		if node.isspace():
			node.replace_with("")
		else:
			node.replace_with(node.rstrip())
			break
	sep = entry.hw.next_sibling
	if isinstance(sep, NavigableString) and sep.lstrip().startswith(","):
		sep.replace_with(sep.lstrip())
	entry.smooth()

def fix_entry(entry):
	for elem in entry:
		if isinstance(elem, Comment):
			elem.decompose()
		elif isinstance(elem, NavigableString):
			elem.replace_with(" ".join(elem.strip().split()))
	for tag in entry.find_all(lambda x: isinstance(x, Tag)):
		if tag.name in ("smallcap", "smallcaps", "smallcpas", "samllcaps"):
			tag.name = "smallcap"
		elif tag.name in ("div", "tam", "i", "b", "hw", "t", "p2", "hw1", "small", "blockquote", "br", "tel", "pos", "uu", "sup", "u", "curly", "curlytext", "sup"):
			pass
		else:
			print(tag.name, repr(entry))
			break

def name(c):
	try:
		return unicodedata.name(c)
	except ValueError:
		return ""

def find_unknown_chars():
	for entry, page in iter_entries("*"):
		text = entry.get_text()
		for c in text:
			if "TAMIL" in name(c) and not c in translit.charset:
				print(name(c))

def find_tags(entry):
	for tag in entry.find_all(lambda t: isinstance(t, Tag)):
		print(tag.name)

# We have the following tags
"""
 279482 tam
 268349 b
 127634 div
 125571 hw
 113007 i
  70652 p2
  51507 pos
   4694 smallcaps
   1930 hw1
    700 small
    698 blockquote
    268 br
    218 tel
     44 uu
     32 sup
     31 u
     13 p2<pos
      5 l.<
      5 curlytext
      5 curly
      3 p2<tam
      2 tma
      2 she
      2 prop.<
      2 heading
      2 a
      1 tam.6<
      1 tam4<
      1 tam35<
      1 tam.17<
      1 tam<10<
      1 smallcpas
      1 siva,
      1 shee
      1 shai
      1 samllcaps
"""

def iter_entries():
	with open("tamil.tsv") as f:
		for line in f:
			line = line.strip()
			fields = line.split("\t")
			assert len(fields) == 3
			yield fields[0], int(fields[1]), fields[2]

substs = [
	"<c>பிரமம்.</c>", "பிரமம்.",
	"[<i>ex</i> <tam>பிரபா</tam> <i><et</i> <tam>கீடம்</tam>", "[<i>ex</i> <tam>பிரபா</tam> <i>et</i> <tam>கீடம்</tam>"
]
s = """
       s.<
       prov.]<
       no<blockquote
       lette
       inf.<
       in
       i<[in
       fem.<
"""
for _, _, text in iter_entries():
	soup = BeautifulSoup(text, "html.parser")
	for tag in s.strip().splitlines():
		tag = tag.strip()
		if soup.find(tag):
			print(repr(tag), soup)
	#find_tags(soup)
