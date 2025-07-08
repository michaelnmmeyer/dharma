# Transforms

We have transforms for various tasks:

	tei2internal
	internal2internal
	internal2search
	internal2html

`tei2internal` must be run first. It converts TEI-encoded XML files to a simpler
XML representation from which we derive everything else. We call this
representation "internal". After this, `internal2internal` must be called. It
performs various operations to validate or fix the internal XML encoding.

At some point we will want to produce PDF or Word files or plain text files. For
this, we should use `pandoc`, but we need to use pandoc's data model. See
https://boisgera.github.io/pandoc/document and more importantly:
https://hackage.haskell.org/package/pandoc-types-1.23.1/docs/Text-Pandoc-Definition.html;
our internal representation must be close enough to this one to allow us to use
pandoc at some point.


# I initially wanted to do validation and display together, with a real parser,
# possibly bound to rng. But in practice, we need to generate a useful display
# even when texts are not valid. So many files are invalid that being too
# strict would leave us with not much, and even so not being able to display a
# text at all because of a single error would be super annoying.



==

Note that link/@href is not mandatory; when it is not given, we mark the link
as invalid.

# TODO turn this into rnc

document: metadata_fields main_division

metadata_fields =
	identifier?
	repository?
	title?
	editor?
	summary?
	hand?

main_divisions:
	edition?
	apparatus?
	translation*
	commentary?
	bibliography?

edition: division
apparatus: division
translation: division
commentary: division
bibliography: division
div: division

division: head division_contents

para_like: para | verse | quote | dlist | list
milestone: npage | nline | ncell

inline = span | link | note | TEXT# If the idea is to convert texts to many formats, we might want to use
# pandoc's data model. See https://boisgera.github.io/pandoc/document
# and more importantly:
# https://hackage.haskell.org/package/pandoc-types-1.23.1/docs/Text-Pandoc-Definition.html
# Our internal representation must be close enough to this one to allow us to
# use pandoc at some point.

note: para+


¶ data fields: title, author, editor
(these elements should not contain paragraphs)
¶ divisions: summary, hand, edition, apparatus, translation, commentary,
bibliography, div
(all their children strings should be removed)
¶ para-like: para verse(>verse-line) head quote
¶ para containers: dlist(>(key, value)) list(>item) note
¶ sub-paragraphs divisions: item, key, value, verse-line
(can only contain inline)



== structural errors in internal2internal

recursively, iter on block-only elements and wrap inlines in paras.

we have structural errors with use of inlines in places where blocks are expected; fixed that for milestones,;see

	if there is no milestone-accepting element, we should end up with just milestones, so put them in a newly-created p.

but remain cases where wrapping is necessary; basically:

within divisions. wrap all child <inline/> elements inside a <para>.

within inlines (span, link, but not note). <inline><block/></inline> ->
unwrap the block (and child blocks)

within blocks. forbid other blocks, thus <para><list/></para>.
	need to set rules for nesting stuff; basically, only divisions
	should hold block elements. otherwise, unwrap the outermost
	block element.

div:  head (block | div)+
head: inline+

verse: verse-head? verse-line+
verse-head: inline+
verse-line: inline+

para: inline+
quote: inline+
list: item+
dlist: (key value)+
note: para+

inline: span | link | milestone | note | TEXT
milestone: npage | nline | ncell
note: restricted_block+

restricted_block: like a normal block but disallowing nested notes

will need to review metadata fields, not sure which we should keep, depends how we do the search stuff.

