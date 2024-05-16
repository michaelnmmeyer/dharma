import sys, re

def repl_gap(m):
	s = m.group(0)
	n = s.count(".")
	return f'<gap reason="lost" quantity="{n}" unit="character" precision="low"/>'

texts = []
text = None
for line in sys.stdin:
	line = line.strip()
	if all(c.isdigit() or c == "-" for c in line):
		text = []
		texts.append((line, text))
	else:
		num = re.match(r"^[0-9]+\.", line)
		assert num, line
		num = num.group(0)[:-1]
		line = line[len(num) + 1:].strip()
		num = f'<lb n="{num}"/>'
		line = line.replace("…", "...")
		line = re.sub(r"\.(\s*\.)*", repl_gap, line)
		text.append(num + line)

tpl = open("DHARMA_INSTamilNadu00401.xml").read()
for ins_no, text in texts:
	n = ins_no.split("-")[0]
	ins_no_padded = "%05d" % (400 + int(n))
	if "-" in ins_no:
		ins_no_padded += "-" + ins_no.split("-", 1)[1]
	contents = "\n".join(text)
	print(ins_no_padded)
	ret = tpl.format(ins_no=ins_no, ins_no_padded=ins_no_padded, contents=contents)
	with open(f"out/DHARMA_INSTamilNadu{ins_no_padded}.xml", "w") as f:
		f.write(ret)

"""
ins_no_padded
ins_no
contents
"""
