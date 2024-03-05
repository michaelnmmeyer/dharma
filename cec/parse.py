import os, sys, unicodedata
from dharma import tree

def tokenize_line(s, stack):
	def push(*args):
		stack[-1].append(args)
	i = 0
	drop_space = False
	while i < len(s):
		c = s[i]
		i += 1
		if c == "%":
			break
		elif c == "\\":
			if not s[i].isalpha():
				push("cmd", s[i])
				i += 1
				drop_space = False
			else:
				start, i = i, i + 1
				while i < len(s) and s[i] not in " {}$\\]-":
					i += 1
				if s[start:i] == "danda*": #DIRTY
					i -= 1
				push("cmd", s[start:i])
				drop_space = True
		elif c == "{":
			stack.append([])
			drop_space = False
		elif c == "}":
			l = stack.pop()
			stack[-1].append(l)
			drop_space = False
		elif c == "$":
			push("math", c)
			drop_space = False
		elif c.isspace():
			if not drop_space:
				push("char", " ")
				drop_space = True
		else:
			push("char", c)
			drop_space = False

def tokenize(f):
	stack = [[]]
	for line in f:
		line = " ".join(line.strip().split()) + " "
		tokenize_line(line, stack)
	assert len(stack) == 1
	return stack.pop()

def diacritic(s, stack, *args):
	i = eval(s, stack)
	c = stack.pop()
	stack.append(c + args[0])
	return i

line_nr = 0
def new_line(s, stack):
	global line_nr
	line_nr += 1
	stack.append(f'\n<lb n="{line_nr}"/>')
	return 0

def grantha(s, stack):
	stack.append(f'<hi rend="grantha">')
	assert isinstance(s[0], list), s[0]
	eval_list(s[0], stack)
	stack.append(f'</hi>')
	return 1

def append(s, stack, c):
	stack.append(c)
	return 0

def drop(s, stack, n):
	return n

def reset_count(s, stack):
	assert isinstance(s[0], list)
	global line_nr
	line_nr = 0
	return 1

cmds = {
	"begin": reset_count,
	"end": [drop, 1],
	"section*": [drop, 1],
	"subsection*": [drop, 1],
	"i": [append, "i"],
	"danda": [append, '|'],
	"ddanda": [append, '||'],
	"tdanda": [append, '|||'],
	"item": new_line,
	"textbf": grantha,
	"index": [drop, 2],
	"footnote": [drop, 1],
	"dots": [append, '<gap reason="lost" extent="unknown" unit="character"/>'],
	" ": [append, " "],
	"Psi": [append, "Ψ"],
	"pm": [append, "±"],
	"'": [diacritic, "\N{COMBINING ACUTE ACCENT}"],
	"`": [diacritic, "\N{COMBINING GRAVE ACCENT}"],
	"^": [diacritic, "\N{COMBINING CIRCUMFLEX ACCENT}"],
	"~": [diacritic, "\N{COMBINING TILDE}"],
	"=": [diacritic, "\N{COMBINING MACRON}"],
	'"': [diacritic, "\N{COMBINING DIAERESIS}"],
	".": [diacritic, "\N{COMBINING DOT ABOVE}"],
	"d": [diacritic, "\N{COMBINING DOT BELOW}"],
	"b": [diacritic, "\N{COMBINING MACRON BELOW}"],
	"c": [diacritic, "\N{COMBINING CEDILLA}"],
	"textsubring": [diacritic, "\N{COMBINING RING BELOW}"],
}

gs = {
	"A": '<g type="undefined"/>',
	"N": '<g type="nilam"/>',
	"K": '<g type="kāṇi"/>',
	"V": '<g type="vēli"/>',
	"M": '<g type="mā"/>',
	"Q": '<g type="muntiri"/>',
	"H": '<g type="mukkāṇi"/>',
	"C": '<g type="kaṇṇāṟu"/>',
	"P": '<g type="nellu"/>',
	"Ā": '<g type="yāṇṭu"/>',
	"M̄": '<g type="mātam"/>',
	"E": '<g type="kiḻ"/>',
	"Z": '<g type="kiḻaṟu"/>',
	"U": '<g type="ulike">.</g>',
}

def add_periods(s, stack):
	i = 0
	while i < len(s):
		cmd, c = s[i]
		if cmd == "char" and c == ".":
			i += 1
			continue
		break
	stack.append(f'<gap reason="lost" quantity="{i + 1}" unit="character"/>')
	return i

def eval_slice(s, stack):
	cmd, c = s[0]
	i = 1
	if cmd == "char":
		if c == ".":
			i += add_periods(s[1:], stack)
		elif c == "(":
			stack.append('<unclear>')
		elif c == ")":
			stack.append('</unclear>')
		elif c == "[":
			stack.append('<supplied reason="lost">')
		elif c == "]":
			# we deal with "*]" -> @reason="subaudible" later on
			stack.append('</supplied>')
		else:
			c = gs.get(c, c)
			stack.append(c)
	elif cmd == "math":
		while s[i][0] != "math":
			i += eval_math(s[i:], stack)
		i += 1
	elif cmd == "cmd":
		data = cmds[c]
		if isinstance(data, list):
			cmd, arg = data
			i += cmd(s[i:], stack, arg)
		else:
			cmd = data
			i += cmd(s[i:], stack)
	return i

eval_math = eval_slice

def eval(s, stack):
	if isinstance(s[0], list):
		eval_list(s[0], stack)
		return 1
	return eval_slice(s, stack)

def eval_list(s, stack):
	i = 0
	while i < len(s):
		i += eval(s[i:], stack)

f = open(sys.argv[1])
num = int(os.path.splitext(os.path.basename(sys.argv[1]))[0])
tokens = tokenize(f)
stack = []
eval_list(tokens, stack)
ret = "".join(stack).lstrip()
ret = unicodedata.normalize("NFC", ret)

out_name = "DHARMA_INSCEC%02d.xml" % num
tpl = open("tpl.xml").read()
tpl = tpl.replace("{{filename}}", os.path.splitext(out_name)[0])
tpl = tpl.replace("{{text}}", ret)
tpl = tpl.replace("{{title}}", "CEC %d" % num)
t = tree.parse_string(tpl)
for node in t.find("//supplied"):
	if node[-1].type == "string" and node[-1].endswith("*"):
		node["reason"] = "subaudible"
		node[-1].replace_with(str(node[-1][:-1]))

with open(f"xml/{out_name}", "w") as f:
	f.write(tree.xml(t))
