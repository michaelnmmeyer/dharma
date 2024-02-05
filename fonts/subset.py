import os, sys, collections
from fontTools.ttLib import TTFont # pip install fonttools
from fontTools.merge import Merger
from glob import glob
from dharma import unicode

def path_of(*relpath):
	return os.path.join(os.path.dirname(__file__), *relpath)

PRODUCERS = {}
def generate(name):
	def decorator(func):
		def wrapper():
			with open(name, "w") as f:
				def write(*args, **kwargs):
					print(*args, **kwargs, file=f)
				func(write)
		assert not name in PRODUCERS
		PRODUCERS[name] = wrapper
		return wrapper
	return decorator

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
		yield start, end, name

def unicode_data(name):
	path = path_of("unidata", name)
	with open(path) as f:
		yield from scan_lines(f)

@generate("charset.txt")
def make_charset(print):
	path = path_of("all_text.txt")
	with open(path) as f:
		chars = set(c for line in f for c in line)
	for c in chars.copy():
		if c.isspace() or c in "\N{bom}\N{zwsp}\N{soft hyphen}":
			chars.remove(c)
	print("".join(sorted(chars)))

def chars_in_font(font):
	chars = set()
	for table in font["cmap"].tables:
		chars.update(chr(c) for c in table.cmap.keys())
	return chars

@generate("missing.txt")
def print_missing(print):
	font_chars = set()
	for file in os.listdir(path_of("selection")):
		font = TTFont(path_of("selection", file))
		font_chars |= chars_in_font(font)
	with open("charset.txt") as f:
		chars = set(f.read().strip())
	for c in chars:
		if c in font_chars:
			continue
		print(unicode.char_name(c), c)

@generate("unicodes.txt")
def make_unicodes(print):
	with open("charset.txt") as f:
		charset = f.read().strip()
	for start, end, name in unicode_data("Blocks.txt"):
		if any(start <= ord(c) <= end for c in charset):
			print("# %s" % name)
			print("%04X-%04X" % (start, end))

def get_font_name(font):
	FONT_SPECIFIER_NAME_ID = 4
	for record in font["name"].names:
		if record.nameID != FONT_SPECIFIER_NAME_ID:
			continue
		name = record.string.decode("UTF-16 BE")
		return name

def extract_ranges(chars):
	chars = sorted(ord(c) for c in chars)
	i = 0
	while i < len(chars):
		j = i
		while j + 1 < len(chars) and chars[j] + 1 == chars[j + 1]:
			j += 1
		if i == j:
			yield "U+%04X" % chars[i]
		else:
			yield "U+%04X-%04X" % (chars[i], chars[j])
		i = j + 1

tpl = """@font-face {
	font-family: '%s';
	font-style: %s;
	font-weight: %s;
	font-stretch: 100%%;
	font-display: swap;
	src: url(/fonts/%s) format('woff2');
	unicode-range: %s;
}"""
def print_font_info(print, file):
	font = TTFont(file)
	name = get_font_name(font)
	chars = chars_in_font(font)
	ranges = ", ".join(extract_ranges(chars))
	style = "Italic" in name and "italic" or "normal"
	if "Mono" in name:
		name = "Noto Mono"
	else:
		# Not all non-monospace fonts are serif, symbols and emojis are
		# not, but I do not think it matters if we say these are serif
		# fonts within the output CSS.
		name = "Noto Serif"
	for weight in (100, 200, 300, 400, 500, 600, 700, 800, 900):
		print(tpl % (name, style, weight, os.path.basename(file), ranges))

# We try to produce something aking to:
# https://fonts.googleapis.com/css2?family=Noto+Sans+Mono:wght@300;400;500;600;700&family=Noto+Serif+Grantha&family=Noto+Serif:ital,wght@0,100;0,200;0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,100;1,200;1,300;1,400;1,500;1,600;1,700;1,800;1,900&display=swap
@generate("fonts.css")
def make_css_file(print):
	for file in glob(path_of("selection/*.woff2")):
		print_font_info(print, file)

if __name__ == "__main__":
	file = sys.argv[1]
	PRODUCERS[file]()
