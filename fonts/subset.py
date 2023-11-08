import sys

# https://codecolibri.fr/optimiser-ses-polices-web-avec-le-font-subsetting/

scripts_to_keep = set("""
Common
#Devanagari
#Greek
Inherited
Latin
""".strip().split())

extensions_to_keep = set("""
#Deva
#Grek
Latn
""".strip().split())


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
		scripts = tuple(script.strip() for script in second.split())
		yield (start, end + 1), scripts

def make_set():
	extended = set()
	chars = set()
	f = open("ScriptExtensions.txt")
	for (start, end), exts in scan_lines(f):
		for char in range(start, end):
			extended.add(char)
		if any(ext in extensions_to_keep for ext in exts):
			for char in range(start, end):
				chars.add(char)
	f = open("Scripts.txt")
	for (start, end), (script,) in scan_lines(f):
		if not script in scripts_to_keep:
			continue
		for char in range(start, end):
			if char in extended:
				continue
			chars.add(char)
	return chars

chars = make_set()
for char in sorted(chars):
	print("%X" % char)

# pyftsubset $f --unicodes-file=unicodes.txt --flavor=woff2 --output-file=`notext $f`-subset.woff2

# pyftsubset $f --unicodes-file=unicodes.txt --output-file=`notext $f`-subset.ttf
