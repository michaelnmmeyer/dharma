## Textpart divisions headings

The values of `div/@subtype`, `div/@n` and `div/head` are taken into account
for generating texpart headings. The relation between these values and their
purpose is not clearly understood by encoders.

Some people reproduce `div/@n` in `div/head`, or even use a different numbering
schemes. Probably because the current behaviour is _either_ to generate a
heading from `div/@subtype` and `div/@n` (Face A, Fragment B, etc.), _or_ to
just display the contents of `div/head`, without displaying `div/@n`. We see
e.g.

```
<div type="textpart" n="4">
<head xml:lang="eng">Face D</head>
```

```
<div type="textpart" subtype="fragment" n="1">
<head xml:lang="eng">Fragment 1</head>
```

There are also confusions between the contents of `div/@subtype` and `div/head`
e.g.

```
<div type="textpart" n="C">
<head xml:lang="eng">Face</head>
```

Instead we should have:

```
<div type="textpart" subtype="face" n="C">
```

The format of `div/head` is also quite variable:

```
<div type="textpart" n="C" resp="part:argr">
<head xml:lang="eng">Plate : first translation</head>
```

```
<div type="textpart" subtype="trial" n="B">
<head xml:lang="eng">Trials unexposed. Left of the main text</head>
```

```
<div type="textpart" subtype="face" n="9">
<head xml:lang="eng">Front: Additional line at bottom</head>
```

I think we should always display the value of `div/@n`, whether a `div/head` is
given or not, if only to make apparent the numbering scheme that will be used
for referencing parts of the inscription. This would also discourage people
from using several numbering schemes together, as seen above.

I propose to format headings as follows. We have 3 possible cases:

```
<div type="textpart" n="1">
<head xml:lang="eng">Upper leftcorner</head>
```

```
<div type="textpart" subtype="fragment" n="1">
```

```
<div type="textpart" subtype="fragment" n="1">
<head xml:lang="eng">Upper left corner</head>
```

These would produce respectively:

	1. Upper left corner

	Fragment 1

	Fragment 1: Upper left corner (OR: Fragment 1. Upper left corner)

The value of `div/@subtype` would not be considered significant for
referencing, so that you cannot have in the same document two textparts that
bear the same `div/@n`, as in

	<div type="textpart" subtype="fragment" n="A">
	...
	<div type="textpart" subtype="face" n="A">

## People names in teiHeader

There are no definite conventions for indicating people's roles. We have
`<respStmt>`, `<editor>`, `<principal>`, `<author>`, etc. depending on files.
In particular, critical editions (DHARMA_CritEd*) do not follow the conventions
adopted in inscriptions (DHARMA_INS*).

I suggest we use a single notation for indicating people's roles. For instance,
to indicate editors, we could either use `<respStmt>` or `<editor>`, but not
both, to avoid confusion.

Inscriptions generally use `<respStmt>`. However, the value of `respStmt/resp`
varies widely between files. Sometimes it contains phrases ("EpiDoc encoding",
etc.), sometimes full sentences, capitalized or not. People treat it as free
text (this is its purpose, according to the TEI documentation), so I cannot
process it mechanically. When people use several `<resp>` for a single
person, it is also not clear how I should merge the values (separate them with
semicolons? with periods? capitalize or not? etc.)

The TEI documentation suggests to add an attribute `resp/@ref` to indicate
people's role in a machine-readable way. See the note at
https://www.tei-c.org/release/doc/tei-p5-doc/en/html/ref-resp.html. From what I
have seen so far, I see at least two distinctions that could be useful for
search and display:

1. The person who is encoding/editing the inscription vs. a source/past edition
from which this person is drawing. I mean the distinction between Salomé Pichon
and George Cœdès, for instance.
2. The person who is doing the core editing work vs. someone that contributed
ideas, a collaborator, etc.

It would also be helpful to constrain the structure of `<respStmt>` in such a way
that the same notation is always used for representing the same data. Compare
the following. A, B and C represent the same data; D is a bit different but is
theoretically possible.

(A)

	<respStmt>
	  <resp>EpiDoc Encoding</resp>
	  <persName ref="part:sapi">
	     <forename>Salomé</forename>
	     <surname>Pichon</surname>
	  </persName>
	</respStmt>
	<respStmt>
	  <resp>intellectual authorship of edition</resp>
	  <persName ref="http://viaf.org/viaf/66465311">
	     <forename>George</forename>
	     <surname>Cœdès</surname>
	  </persName>
	  <persName ref="part:sapi">
	     <forename>Salomé</forename>
	     <surname>Pichon</surname>
	  </persName>
	</respStmt>

(B)

	<respStmt>
	  <resp>EpiDoc Encoding</resp>
	  <persName ref="part:sapi">
	     <forename>Salomé</forename>
	     <surname>Pichon</surname>
	  </persName>
	</respStmt>
	<respStmt>
	  <resp>intellectual authorship of edition</resp>
	  <persName ref="http://viaf.org/viaf/66465311">
	     <forename>George</forename>
	     <surname>Cœdès</surname>
	  </persName>
	</respStmt>
	  <resp>intellectual authorship of edition</resp>
	  <persName ref="part:sapi">
	     <forename>Salomé</forename>
	     <surname>Pichon</surname>
	  </persName>
	</respStmt>

(C)

	<respStmt>
	  <resp>EpiDoc Encoding</resp>
	  <resp>intellectual authorship of edition</resp>
	  <persName ref="part:sapi">
	     <forename>Salomé</forename>
	     <surname>Pichon</surname>
	  </persName>
	</respStmt>
	<respStmt>
	  <resp>intellectual authorship of edition</resp>
	  <persName ref="http://viaf.org/viaf/66465311">
	     <forename>George</forename>
	     <surname>Cœdès</surname>
	  </persName>
	</respStmt>

(D)

	<respStmt>
	  <resp>EpiDoc Encoding</resp>
	  <resp>intellectual authorship of edition</resp>
	  <persName ref="part:sapi">
	     <forename>Salomé</forename>
	     <surname>Pichon</surname>
	  </persName>
	  <persName ref="http://viaf.org/viaf/66465311">
	     <forename>George</forename>
	     <surname>Cœdès</surname>
	  </persName>
	</respStmt>

## Numbering of chapters, verses, milestones, etc.

We want to be able to refer to precise locations in a document, as in A2, 1.1,
3r1, etc. We want these locations to be unique. For now, this is rather
difficult.

Indeed, we allow both a repetitive scheme (within a `<div n="A">`, we
have A.1, A.2, A.3, etc.) and a non-repetitive one (within a `<div n="A">`, we
have 1, 2, 3). Since there are no particular constraints on number formats, it
is not possible for a program to tell, in the general case, whether `@n` holds
a single number or combines several. For instance, should "A1" be interpreted
as `[A1]` (one level) or `[A, 1]` (two levels)? I need an explicit indication
that allows me to tell unambiguously which scheme we have, or at least a single
numbering convention. Maybe enforce the use of a single field separator
(period, etc.)?

There is also a difficulty with the uniqueness of `@n`s. When dealing merely
with elements that represent the logical structure and that nest within each
other (`<div>`, `<lg>`, `<l>`, etc.), producing a reference number and checking
its uniqueness is straightforward, because the scope of elements and the way
they nest is explicit in the XML. But when we introduce elements that represent
the physical structure (`<lb>`, `<milestone>`, `<pb>`), it is not clear at all.

Firstly, because the extent of these elements is unspecified. For instance,
when does a `<milestone unit="face"/>` end? When the next milestone with an
identical `@unit` begins? We also have `<milestone unit="faces"/>`.

Secondly, because it is unspecified how these elements can nest with each other
and with logical elements. For instance, can a `<milestone unit="zone">`
contain a `<milestone unit="column">`? Or the reverse? Or both? Or maybe they
have no relation whatsoever and should be treated independently, like e.g.
`<lb/>` and `<p>`.

Generally speaking, I cannot do much with milestone-like elements, precisely
because I cannot tell how they relate to each other and to the logical
structure. The physical display is very fragile for this reason, and I am not
even speaking about search.

## Referencing documents, parts of documents, bibliographic entries, etc.

This is related to the last point.

We are currently using a variety of reference systems. For instance:

```
<p n="3" corresp="#siksaguru_01.03"> (points to <p xml:id="siksaguru_01.03"> in another file)
<change who="part:axja" ...>
<persName ref="http://viaf.org/viaf/39382787">
<licence target="https://creativecommons.org/licenses/by/4.0/">
<ref>DHARMA_IdListMembers_v01.xml</ref>
<ref target="DHARMA_INSCIK00288.xml">
<idno type="filename">DHARMA_INSCIK00803</idno>
<rdg source="bib:Coedes1942_02">
```

The use of `corresp="#siksaguru_01.03"` for referencing an `@xml:id` in another
document is problematic. An `@xml:id` is supposed to be unique within a single
document, not at the scope of a full document collection. A typical address for
part of a document is `DHARMA_INSHello#location`, where `DHARMA_INSHello` is
the file name and `location` is an `@xml:id`. When referencing something in
the same document, the filename is not necessary, `#location` suffices.

We can choose not to follow XML conventions, but in any case, we
must have a referencing scheme that clearly distinguishes the file name and the
location of the target element within this file. Otherwise, I basically have to
process all the files in the collection to figure out where the `@xml:id` lies,
instead of processing a single file.

Secondly, we need to be careful to avoid name clashes in references. For
instance, we cannot have both `DHARMA_INSHello_1.2.3` for referencing a
`@n=1.2.3` and `DHARMA_INSHello_location` for referencing an
`@xml:id=location`, because it is not possible to tell from the reference
itself whether it refers to a `@n` or to an `@xml:id`.

## Gaiji

The usage of `<g>` seems to have changed over time. People typically put a
textual representation of the symbol within the `<g>` element, as in `<g
type="ddanda">||</g>` or even `<g>||</g>`, although the guide says to do things
differently. There are many problems of this type.

## Scripts

Only about 1/4 of texts use `@rendition` to specify scripts. I suspect it is
because scripts are represented with unreadable identifiers from OpenTheso, as
in `rendition="class:83225 maturity:83213"`. The relevant page on OpenTheso is
https://opentheso.huma-num.fr/opentheso/?idt=th347 (links in the EGD are no
longer valid).

People apparently do not know what they should choose for `maturity`, and there
are scripts for which the available values of `maturity` make no sense (e.g.
"Chinese script"), so we could make it optional.

For script classes, we currently have a hierarchy e.g. `/Brāhmī and
derivatives/southern class Brāhmī/Tamil script/Tamil with Grantha`. This
hierarchy is not apparent in the encoding used in inscriptions, and people can
choose either a class that has children (e.g. "Tamil script") or a class that
does not (e.g. "Tamil with Grantha"). I do not think they see the difference,
if only because the contextual help generated from our schemas does not make it
explicit. Things would probably be clearer if the hierarchy was flattened a bit.

To simplify the encoding, I suggest we allow script names (or ISO 15924 script codes,
when available) in place of integers. For instance, we could have
`rendition="class:Sundanese"` or `rendition="class:Sund"` or even
`rendition="Sund"`, which would then be mapped to the internal id `class:57470` that is
used in OpenTheso.

## Language codes (table in the appendix of the EGD).

In ISO 639-3, the proper code for "Undetermined Language" is "und", not
"unknown".

For "x-oldbalinese", we should submit a change request (here:
https://iso639-3.sil.org/code_changes/submitting_change_requests). Apparently,
the language codes "oba" and "obn" are free.

Language codes enumerated in the table belong to ISO 639-3, but "pra" (Prakrit
languages) belongs to ISO 639-5, it designates a family of languages. There are
also individual language codes in ISO 639-3, namely:

	pka	Ardhamāgadhī Prākrit
	pmh	Māhārāṣṭri Prākrit
	psu	Sauraseni Prākrit

Indicate in the table to use "pra" instead of these?
