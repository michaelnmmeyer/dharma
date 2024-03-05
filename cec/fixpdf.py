import sys, io, unicodedata

# "i": [append, "i"],
# "d": [diacritic, "\N{COMBINING DOT BELOW}"],
# "b": [diacritic, "\N{COMBINING MACRON BELOW}"],
# "c": [diacritic, "\N{COMBINING CEDILLA}"],

foll = {
	"'": "\N{COMBINING ACUTE ACCENT}",
	"`": "\N{COMBINING GRAVE ACCENT}",
	"^": "\N{COMBINING CIRCUMFLEX ACCENT}",
	"~": "\N{COMBINING TILDE}",
	"=": "\N{COMBINING MACRON}",
	'"': "\N{COMBINING DIAERESIS}",
	".": "\N{COMBINING DOT ABOVE}",
}
foll2 = {
	"d": "\N{COMBINING DOT BELOW}",
	"b": "\N{COMBINING MACRON BELOW}",
	"c": "\N{COMBINING CEDILLA}",
}

s = sys.stdin.read()
s = s.replace("\\textsubring{r}", "r\N{combining ring below}")
s = s.replace("\\textsubring{R}", "R\N{combining ring below}")

buf = io.StringIO()
out = buf.write

i = 0
while i < len(s):
	c = s[i]
	i += 1
	if c == '\\':
		if not s[i].isalpha() and s[i] in foll:
			acc = foll[s[i]]
			i += 1
			if s[i].isalpha():
				out(s[i] + acc)
				i += 1
			else:
				assert s[i:i + 2] == "\\i" and not s[i + 2].isalnum()
				out("i" + acc)
				i += 2
				while s[i].isspace() and s[i] != '\n':
					i += 1
		elif s[i] in foll2 and not s[i + 1].isalpha():
			acc = foll2[s[i]]
			i += 1
			while s[i].isspace():
				i += 1
			if s[i].isalpha():
				out(s[i] + acc)
				i += 1
			else:
				assert s[i:i + 2] == "\\i" and not s[i + 2].isalnum()
				out("i" + acc)
				i += 2
				while s[i].isspace() and s[i] != '\n':
					i += 1
		else:
			out(c)
	else:
		out(c)

buf = buf.getvalue()
buf = unicodedata.normalize("NFC", buf)
sys.stdout.write(buf)
