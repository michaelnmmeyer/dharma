import sys
from dharma import tree

"""
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
	<S> = No. (inscription num given in the leftmost column)
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

class State:

	def __init__(self):
		self.stk = []
		self.number = self.page = 0

	def clear(self):
		self.stk.clear()
		self.number = self.page = 0

def handle_inscription(state, elem):
	print(elem.xml())

def parse_file(path):
	t = tree.parse(path)
	state = State()
	for doc in t.find("//doc"):
		state.stk.clear()
		for elem in doc:
			if not is_a_tag(elem):
				continue
			if elem.name.startswith("H"):
				handle_title(state, elem)
			elif elem.name == "INSCRIPTION":
				handle_inscription(state, elem)
			elif elem.name == "Footnote":
				pass
			else:
				assert 0
	print(t)

for f in sys.argv[1:]:
	parse_file(f)
