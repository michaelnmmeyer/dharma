import os, sys, io, sqlite3, unicodedata
from bs4 import BeautifulSoup, NavigableString, Comment, Tag
import translit

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

def page_from_url(url):
	return int(url.rsplit("=", 1)[1])

db = sqlite3.connect("tamil.sqlite")
db.create_function("page_from_url", 1, page_from_url, deterministic=True)

def raw_fix(page):
	page = page.replace("<tam>6</tam - இன் இல், நின்று", "<tam>6</tam> - இன் இல், நின்று")
	return page

def iter_entries(dict_name):
	for url, page, data in db.execute("""
		select url, page_from_url(url) as page, data from raw_pages
		where url glob ? order by page""", ("*%s_query*" % dict_name,)):
		data = raw_fix(data)
		soup = BeautifulSoup(io.StringIO(data), "html.parser")
		root = soup.find("div", class_="hw_result")
		for div in root.find_all("div"):
			yield url, div, page

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

def find_tags():
	for entry, page in iter_entries("*"):
		for tag in entry.find_all(lambda t: isinstance(t, Tag)):
			print(tag.name)

# We have the following tags
"""
 684238 tam
 308299 i
 268567 b
 243377 hw
 168520 pos
 117803 t
  70652 p2
  28479 smallcap
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
      4 a
      3 td
      3 p2<tam
      2 tma
      2 she
      2 prop.<
      2 heading
      2 div
      2 c
      1 tr
      1 tam.6<
      1 tam4<
      1 tam35<
      1 tam.17<
      1 tam<10<
      1 table
      1 smallcpas
      1 siva,
      1 shee
      1 shai
      1 samllcaps
      1 s.<
      1 prov.]<
      1 no<blockquote
      1 lette
      1 inf.<
      1 in
      1 i<[in
      1 fem.<
      1 et<
"""

for url, entry, page in iter_entries("*"):
	if len(entry.find_all("div")) > 0:
		print(url)
