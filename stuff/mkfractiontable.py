import requests, csv, io, re

NAME_COLUMN = 1
DECOMP_COLUMN = 5

r = requests.get("https://www.unicode.org/Public/UCD/latest/ucd/UnicodeData.txt")
rows = csv.reader(io.StringIO(r.text), delimiter=";")
tbl = {}
for row in rows:
	m = re.fullmatch(r"<fraction> ([0-9A-Fa-f]+) 2044 ([0-9A-Fa-f]+)", row[DECOMP_COLUMN])
	if not m:
		continue
	name = row[NAME_COLUMN]
	num, den = m.group(1), m.group(2)
	num, den = int(num, 16), int(den, 16)
	num, den = chr(num), chr(den)
	tbl[name] = (num, den)

rev = {}
for k, v in tbl.items():
	assert not v in rev
	rev[v] = k

for k, v in sorted(rev.items()):
	print('(%s, %s): "\\N{%s}",' % (k[0], k[1], v.lower()))
