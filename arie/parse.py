"""

PDFs:
https://sharedocs.huma-num.fr/#/3491/40760/J-ARIE



<root>
<doc> is sub-root

in each doc have
	<H1><arie n="001" ref="ARIE1886-1887"/>...</H1>

c'est normal que la numérotation des arie/@n ne soit pas continue

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
	hard line breaks to remove from each field.


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
	@type is one of "subdistrict" "district" "state" "placename"
	dans l'original est centré dans la colonne "Place of inscription"

	<H type="district">DHARWAR DISTRICT</H>
		capitales et centré
	<H type="subdistrict">Ron Taluk</H>
		petites caps et centré

	difficile à extraire pour la recherche

<apb>	indique que l'enregistrement se poursuit sur la page suivante;
	le marqueur est présent dans chaque colonne qui se poursuit sur
	la page suivante. info pas très utile, sauf pour renvoyer à des
	numéros de page de l'édition papier. pas vérifié si des entrées
	s'étendent sur plus de deux pages viz. s'il peut y avoir plusieurs
	<apb> dans une seule entrée.

weird:
	<Footnote> (l'une d'elle est précédée de <sup> [1 seule occ.] pour l'appel)



"""