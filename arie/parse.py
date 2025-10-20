import sys, re
from dharma import tree

"""
créer un display pour chaque année; et recherche sur tout le contenu.

first file we have:
<!--<p>Ā A2 A4 Ã Ä A9 B1 B2 B9 C1 C3 C4 C6 D1 Ḍ D4 D5 D6 E1 E2 E4 E5 Ë F1 G6 H2 Ī I2 I4 Ï K1 K2 K6
Ḷ L6 M3 M7 Ṇ Ṅ Ñ N6 O1 O4 Õ P1 Q4 Ṛ R6 S1 Ṣ Ś S6 Ṭ T6 Ū U5 Ü V6 ā a2 a3 a4 ã a6 ä c1
ḍ d6 e0 ē e4 e5 ë g6 h2 h6 ī i2 i4 i5 ï i9 k2 ḵ l1 ḷ ḻ ṃ ṁ m6 n1 ṇ ṅ n4 ñ ṉ n7 o0 ō
o3 o4 õ o6 ö o8 o9 p2 p6 ṛ r3 ṟ r7 ṣ s3 ś s6 ṭ t6 t8 ū u2 u3 u4 u5 u6 ü u8 v2 v3 v4 v7 x3
x4 x7 y3 z2 z6</p>-->
look how evolved and also see if we sth similar in second file.

transférer ARIE sur nouveau site. outil de recherche
copyrighted from 1959-60 onwards, add a password for consulting them.

first deal with nesting of headings, place each inscription under an explicit heading

reproduire numérotation (cf. manu tiruvava10004 pour exemple); ensuite, ajouter des liens dans le fichier principal.

PDFs:
https://sharedocs.huma-num.fr/#/3491/40760/J-ARIE

<root>
<doc> is sub-root

in each doc have
	<H1><arie n="001" ref="ARIE1886-1887"/>...</H1>

c'est normal que les arie/@n soient pas numérotés consécutivement

<INSCRIPTION>
	<S> = (serial?) No. (inscription num given in the leftmost column)
	<P> = Place
	<K> = King
	<D> = Date
	<L> = Language & Alphabet
	<Y> = Dynasty
	<R> = Remarks
	<O> = Origin
	<E> = Edition
	<RY> = Regnal Year
	<SY> = Sáka Year
	<JY> = Jovian Year
	<MM> = Madras Map Survey Number
	<MST> = Manuscript's Title
	<MSL> = Manuscript's Language
	<MSE> = Manuscript's extent

within fields:
	<lb> avec @break
	<pb> avec @break; @n du type "056:04" = vol. 56 p. 4
	<i> italics
	<b> bold
	<tamil> text in some transliteration scheme to be transliterated
	hard line breaks (in contrast with <lb> to remove from each field).

dans les remarques on a généralement un paragraphe pour chaque inscription, mais
des fois plusieurs. hanging indent for paragraphs in the original.

<supplied reason="subaudible"> toujours cette forme, avec deux exceptions:
	<supplied>3</supplied>
	<supplied reason="omitted">r</supplied>

H, H1, H2, H3, H4
	differences in formatting?

<H1>
	toujours employé pour des numéros d'ARIE, on a:

	<H1><arie n="088" ref="ARIE1969-1970"/>filename arie088_(1969-1970)_pp.16-77.txt</H1>

<H>
	level relative to H[1-4]?

	@type is one of "subdistrict" "district" "state" "placename"
	in the original centred in column "Place of inscription"
	it looks like the (implicit) hierarchy is:

		"state" > "district" > "subdistrict" > "placename"

	can't do much besides displaying a heading for now.

	<H type="district">DHARWAR DISTRICT</H>
		capitales et centré
	<H type="subdistrict">Ron Taluk</H>
		petites caps et centré

	tell manu the H should be assigned levels to be searchable

<apb>	indique que l'enregistrement se poursuit sur la page suivante;
	le marqueur est présent dans chaque colonne qui se poursuit sur
	la page suivante. info pas très utile, sauf pour renvoyer à des
	numéros de page de l'édition papier. pas vérifié si des entrées
	s'étendent sur plus de deux pages viz. s'il peut y avoir plusieurs
	<apb> dans une seule entrée.

<Footnote>
	drop for now?
"""

def handle_title(state, elem):
	if elem.name == "H":
		# Can't deal with this
		return
	level = int(elem.name[1:])
	while len(state.stk) >= level:
		state.stk.pop()
	state.stk.append(elem)

def is_a_tag(elem):
	match elem:
		case tree.Tag():
			return True
		case tree.String():
			assert not elem.data.strip()
	return False

INSCRIPTIONS = []
INSCRIPTIONS_MAP = {}

class State:

	def __init__(self):
		self.stk = []
		self.clear()

	def clear(self):
		self.stk.clear()
		self.arie_no = 0
		self.pub_year_start = 0
		self.pub_year_end = 0
		self.pub_year_index = 0
		self.study_date = 0
		self.page_no = 0
		self.appendix_no = 0

	def __repr__(self):
		return f"State(arie_no={self.arie_no}, pub_year_start={self.pub_year_start}, pub_year_end={self.pub_year_end}, pub_year_index={self.pub_year_index}, study_year={self.study_year}, page_no={self.page_no})"

class Inscription:

	def __init__(self, state, serial_no):
		self.arie_no = state.arie_no
		self.pub_year_start = state.pub_year_start
		self.pub_year_end = state.pub_year_end
		self.pub_year_index = state.pub_year_index
		self.study_date = state.study_date
		self.page_no = state.page_no
		self.appendix_no = state.appendix_no
		self.serial_no = serial_no

	@property
	def indent(self):
		return f"/ARIE/{self.pub_year_start}-{self.pub_year_end}({self.pub_year_index})/{self.appendix_no}/{self.study_year}/{self.serial_no}"

"""
Idents of the form:
/ARIE/1917-1918/C/1918/4

/ARIE/$pub_year_start-$pub_year_end/$appendix_no/$study_date/$serial_no

arie_no = H1/arie[@n]
pub_date = extract from H1/arie[@ref]

	<arie n="040" ref="ARIE1917-1918"/>
	<arie n="002" ref="ARIE1887-1888_01"/>

pub_index = extract from H1/arie[@ref]

	<arie n="040" ref="ARIE1917-1918"/>	extract 0
	<arie n="002" ref="ARIE1887-1888_01"/>	extract 1

appendix_no = fetch from H2 e.g.

	<H2>APPENDIX A.—List of copper-plates examined during the year 1917-18. <pb n="040:11"/></H2>

study_date = fetch from H2 when possible, e.g.:

	<H2>APPENDIX A.—List of copper-plates examined during the year 1917-18. <pb n="040:11"/></H2>

serial_no = contents of INSCRIPTION/S

"""

def parse_inscription(state, elem):
	n = elem.first("S").text()
	ins = Inscription(state, str(n))
	return ins

def parse_h1(state, elem):
	arie = elem.first("arie")
	state.arie_no = int(arie["n"].lstrip("0"))
	ref = arie["ref"]
	m = re.match(r"^ARIE([0-9]{4})-([0-9]{4})(_0[1-9])?$", ref)
	assert m, ref
	state.pub_year_start = int(m.group(1))
	state.pub_year_end = int(m.group(2))
	if (idx := m.group(3)):
		state.pub_year_index = int(idx[2:])

def parse_pb(state, elem):
	n = elem["n"]
	m = re.match(r"^([0-9]+):([0-9]+)$", n)
	assert m, n
	arie_no = int(m.group(1).lstrip("0"))
	assert arie_no == state.arie_no
	page_no = int(m.group(2).lstrip("0"))
	assert page_no > 0
	assert state.page_no < page_no, f"{state!r} < {page_no}"
	state.page_no = page_no

def parse_h2(state, root):
	for elem in root.children():
		if elem.name == "pb":
			parse_pb(state, elem)
			elem.unwrap()
		elif elem.name == "note":
			elem.delete()
	text = root.text()
	print(text)

def parse_file(path):
	t = tree.parse(path)
	state = State()
	for doc in t.find("//doc"):
		state.clear()
		for elem in doc:
			if not is_a_tag(elem):
				continue
			elif elem.name == "H1":
				parse_h1(state, elem)
			elif elem.name == "H2":
				parse_h2(state, elem)
			elif elem.name.startswith("H"):
				pass
			elif elem.name == "INSCRIPTION":
				parse_inscription(state, elem)
			elif elem.name == "note":
				pass
			else:
				assert 0

for f in sys.argv[1:]:
	parse_file(f)
