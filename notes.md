## People names in teiHeader

There are no conventions for indicating people's roles. We have
`<respStmt><resp>xxx</resp>...`, `<editor role=xxx>`, `<principal>` depending
on files.

I suggest we use `<respStmt>` only and allow a single occurrence of it for each
person. Having several occurrences is annoying because `<resp>` contains free
text, sometimes single words, sometimes phrases, thus I cannot tell how to
merge the distinct values (period between them? capitalize or not? etc.).

It would also be useful to define a set of possible `<resp>`: "editor",
"collaborator", etc. See
https://www.tei-c.org/release/doc/tei-p5-doc/en/html/ref-resp.html for an
example. It uses the values in https://id.loc.gov/vocabulary/relators.html.

## Numbering of chapters, verses, milestones, etc.

We want to be able to refer to precise locations in a document, as in A.1, 3r1,
etc. We want these locations to be unique.

Right now, this is not possible.

Indeed, the guide allows both a repetitive scheme (within a `<div n="A">`, we
have A.1, A.2, A.3, etc.) and a non-repetitive one (within a `<div n="A">`, we
have 1, 2, 3). Since there are no particular constraints on number formats, it
is not possible for a program to tell, in the general case, whether @n holds a
single number or combines several. I need an explicit indication that allows me
to tell unambiguously which scheme we have. Maybe enforce the use of a single
field separator (period, etc.)?

There is also a difficulty with the uniqueness of `@n`s. It is not said
explicitly within which scope each milestone, etc. should be unique. For
instance, we have a "column" milestone that apparently must be unique within a
physical line (`<lb>`). But there is no explicit relationship between the two
milestones (can a line contain columns? does the contrary happen? are the two
related at all? where does a line end? and a column? etc.). Since the guide
allows the addition of custom milestones, it gets even more complicated.

Checking the uniqueness of the @n of logical elements (`<div>, `<lg>`, etc.)
can be made reliable, because the scope is explicit in the document's
structure, but checking the uniqueness of physical elements is messy, if
at all possible.

## Referencing documents, parts of documents, bibliographic entries, etc.

This is related to the last point.

Right now, we have many ways to label or reference objects (`@xml:id`, `<ptr>`,
`<ref>`, `@corresp`, prefixes like `bib:`, etc.) This is messy to implement. It
would make things much simpler for me if we agreed on a common mechanism.

Firstly, it must be noted that XML traditionally uses URLs to identify external
documents or locations in the same document. Thus a typical address for a part
of a document is `DHARMA_INSHello#location`, where `DHARMA_INSHello` is the
file name and `location` is an `@xml:id`. When referencing something from the
document itself, adding the filename is not necessary, `#location` suffices.

There are no names clash between DHARMA texts viz. they have names that are
unique across all DHARMA texts. But we also need to reference bibliographic
entries, and (in the future) images, etc. We can choose to also put these items
in the same namespace or in a different one, I am not sure which is more
convenient.

For instance, we can decide to name all images DHARMA_IMGxxxx, and
bibliographic entries DHARMA_BIBxxxx. An annoying thing with the "global
namespace" thing is that it is not easy for people to detect duplicates,
especially when they are put into different repositories, since we can have the
same filename in two different directories. Duplicates are found when updating
the database, but still, this is messy.

## Gaiji

The usage of `<g>` seems to have changed over time. People typically put a
textual representation of the symbol within the `<g>` element, although the
guide says to do things differently.

I have copied into a machine-readable table the symbol names and textual
representations mentioned in the guide. See my post in project-documentation.

## Scripts

Not many people use @rendition to specify scripts, although it would be a
useful search criterion. I suspect it is because they are noted with
meaningless identifiers as in `rendition="class:83225 maturity:83213"`, which
is unreadable. Use more meaninfgul identifiers? (they can be mapped to the
taxonomy of OpenTheso if needed).

## Language codes, the table in the appendix of the EGD.

In ISO 639-3, the proper code for "Undetermined Language" is "und", not
"unknown".

For x-oldbalinese, should submit a change request (here:
https://iso639-3.sil.org/code_changes/submitting_change_requests). Apparently,
"oba" and "obn" are free.

Language codes enumerated in the table belong to ISO 639-3, but "pra" (Prakrit
languages) belongs to ISO 639-5, it designates a family of languages. There are
also individual language codes, namely:

	pka	Ardhamāgadhī Prākrit
	pmh	Māhārāṣṭri Prākrit
	psu	Sauraseni Prākrit

Indicate in the table to use "pra" instead of these?
