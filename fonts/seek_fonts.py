# Finds fonts that include one or more code points

import sys, os, unicodedata, argparse
import chardet				# pip install chardet
from fontTools.ttLib import TTFont	# pip install fonttools

FONTS_PATHS = [
	# Add here the location of noto repositories
	"selection"
]

def is_font_file(file):
	return os.path.splitext(file)[1] in (".otf", ".ttf", ".ttc")

def font_files(path):
	path = os.path.expanduser(path)
	path = os.path.expandvars(path)
	if not os.path.exists(path):
		return
	if os.path.isfile(path):
		if is_font_file(path):
			yield path
	else:
		for root, dirs, files in os.walk(path):
			for file in files:
				if is_font_file(file):
					yield os.path.join(root, file)

def all_font_files(paths):
	return (file for path in paths for file in font_files(path))

def get_font_name(font):
	FONT_SPECIFIER_NAME_ID = 4
	recs = font["name"].names
	rec = recs[FONT_SPECIFIER_NAME_ID - 1]
	name = rec.string.decode("UTF-8")
	return name

def get_font_chars(font):
	cs = set()
	for table in font["cmap"].tables:
		cs.update(table.cmap.keys())
	return cs

def get_matching_fonts(paths, chars):
	fonts = {}
	for font_path in all_font_files(paths):
		font = TTFont(font_path, fontNumber=0)
		font_name, font_chars = get_font_name(font), get_font_chars(font)
		font.close()
		if font_chars.issuperset(chars):
			fonts.setdefault(font_name, set()).add(font_path)
	return fonts

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Locate fonts that can display a set of characters")
	parser.add_argument("char", nargs="*", help="a character to look for")
	args = parser.parse_args()
	chars = set()
	for char in args.char:
		if len(char) > 1:
			char = int(char, 16)
		else:
			char = ord(char)
		chars.add(char)
	font_names = get_matching_fonts(FONTS_PATHS, chars)
	for name, paths in sorted(font_names.items()):
		print(name, ",".join(sorted(paths)))
