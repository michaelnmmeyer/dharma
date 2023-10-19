import sys, unicodedata

# https://www.unicode.org/charts/PDF/U0B80.pdf

L = lambda s: unicodedata.lookup("tamil letter %s" % s)
S = lambda s: unicodedata.lookup("tamil sign %s" % s)
V = lambda s: unicodedata.lookup("tamil vowel sign %s" % s)
D = lambda s: unicodedata.lookup("tamil digit %s" % s)

vowels = {
	"a": L("a"),
 	"ā": L("aa"),
	"i": L("i"),
	"ī": L("ii"),
	"u": L("u"),
	"ū": L("uu"),
	"e": L("e"),
	"ē": L("ee"),
	"ai": L("ai"),
	"o": L("o"),
	"ō": L("oo"),
	"au": L("au"),
}

virama = S("virama")

intra_vowels = {
 	"ā": V("aa"),
	"i": V("i"),
	"ī": V("ii"),
	"u": V("u"),
	"ū": V("uu"),
	"e": V("e"),
	"ē": V("ee"),
	"ai": V("ai"),
	"o": V("o"),
	"ō": V("oo"),
	"au": V("au"),
}

consonants = {
	"k": L("ka"),
	"ṅ": L("nga"),
	"c": L("ca"),
	"j": L("ja"),
	"ñ": L("nya"),
	"ṭ": L("tta"),
	"ṇ": L("nna"),
	"t": L("ta"),
	"n": L("na"),
	"ṉ": L("nnna"),
	"p": L("pa"),
	"m": L("ma"),
	"y": L("ya"),
	"r": L("ra"),
	"ṟ": L("rra"),
	"l": L("la"),
	"ḷ": L("lla"),
	"ḻ": L("llla"),
	"v": L("va"),
	"ś": L("sha"),
	"ṣ": L("ssa"),
	"s": L("sa"),
	"h": L("ha"),
}

other = {
	"ṃ": S("anusvara"),
	"ḥ": S("visarga"),
	"oṃ": "\N{tamil om}",
	"0": D("zero"),
	"1": D("one"),
	"2": D("two"),
	"3": D("three"),
	"4": D("four"),
	"5": D("five"),
	"6": D("six"),
	"7": D("seven"),
	"8": D("eight"),
	"9": D("nine"),
	"10": "\N{tamil number ten}",
	"100": "\N{tamil number one hundred}",
	"1000": "\N{tamil number one thousand}",
	"\N{tamil day sign}": "\N{tamil day sign}",
	"\N{tamil month sign}": "\N{tamil month sign}",
	"\N{tamil year sign}": "\N{tamil year sign}",
}

def reverse_dict(t):
	ret = {}
	for k, v in t.items():
		ret[v] = k
	return ret

vowels = reverse_dict(vowels)
intra_vowels = reverse_dict(intra_vowels)
consonants = reverse_dict(consonants)
other = reverse_dict(other)

ignore = {virama}

charset = set(vowels) | set(intra_vowels) | set(consonants) | set(other) | ignore

def name(c):
	try:
		return unicodedata.name(c)
	except ValueError:
		return ""

def translit(s):
	i = 0
	buf = []
	while i < len(s):
		c = s[i]
		r = consonants.get(c)
		if r:
			buf.append(r)
			i += 1
			if i == len(s):
				buf.append("a")
			elif s[i] == virama:
				i += 1
			elif s[i] not in intra_vowels:
				buf.append("a")
			continue
		if c in ignore:
			i += 1
			continue
		r = vowels.get(c) or intra_vowels.get(c) or other.get(c)
		if not r and "TAMIL" in name(c):
			raise Exception(c, name(c))
		buf.append(r or c)
		i += 1
	return "".join(buf)

"""

ś is š in tamil-lex

k->g
t->d
p->b
ḥ->ḵ

ttal
tal
ḷu
ṇu

https://dsal.uchicago.edu/dictionaries/crea

"""

if __name__ == "__main__":
	for line in sys.stdin:
		line = line.rstrip().replace("-", "")
		#left, right = line.split("\t")
		left=line
		repl = translit(left).replace(" ", "").removesuffix("ttal").removesuffix("tal").removesuffix("(ḷu)").removesuffix("[ṇu]")
		repl = "".join(c for c in repl if not "SUPERSCRIPT" in name(c))
		#if repl == right:
		#	continue
		#print(right, repl, left, sep="\t")
		print(left, repl, sep="\t")
