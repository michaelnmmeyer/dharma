<!--
% rebase("base.tpl", title="Documentation")
-->

<div class="body">

# Documentation

This is a complement to the various guides of the project. It addresses some
issues that are not covered by the guides, and points out how I deviate from
the guidelines, when I do deviate from them.

## Schemas

You can consult here the TEI documentation generated from DHARMA schemas. You
should follow this instead of the [documentation on the TEI
website](https://www.tei-c.org/release/doc/tei-p5-doc/en/html/index.html),
because our schemas are more restrictive. Even so, they are more permissive
than they should.

We currently have four schemas. The schema used to validate a given text is
inferred from the file name. I ignore processing instructions that tell which
schemas should be used for validating texts, viz. all this stuff:

	<?xml-model href="https://raw.githubusercontent.com/erc-dharma/project-documentation/master/schema/latest/DHARMA_Schema.rng" type="application/xml" schematypens="http://relaxng.org/ns/structure/1.0"?>
	<?xml-model href="https://raw.githubusercontent.com/erc-dharma/project-documentation/master/schema/latest/DHARMA_Schema.rng" type="application/xml" schematypens="http://purl.oclc.org/dsdl/schematron"?>
	<?xml-model href="https://raw.githubusercontent.com/erc-dharma/project-documentation/master/schema/latest/DHARMA_SQF.sch" type="application/xml" schematypens="http://purl.oclc.org/dsdl/schematron"?>
	<?xml-model href="https://epidoc.stoa.org/schema/latest/tei-epidoc.rng" schematypens="http://relaxng.org/ns/structure/1.0"?>
	<?xml-model href="https://epidoc.stoa.org/schema/latest/tei-epidoc.rng" schematypens="http://purl.oclc.org/dsdl/schematron"?>

I will delete these and replace them eventually.

Our schemas are:

<ul>
<li><a href="/documentation/inscription">Inscriptions</a> (files named
DHARMA_INS*)</li>
<li><a href="/documentation/diplomatic">Diplomatic editions</a> (files named
DHARMA_DiplEd*)</li>
<li><a href="/documentation/critical">Critical editions</a> (files named
DHARMA_CritEd*)</li>
<li><a href="/documentation/bestow">BESTOW</a> (no file naming
convention)</li>
</ul>

Encoded texts generally deviate from the guidelines, and it is unreasonable to
expect people to come back to them again and again, as I discover new issues.
Thus, I try to do something sensible whenever possible viz. whenever something
can be mechanically inferred.

Here are a few notes on how XML files are interpreted. This only concerns
inscriptions for now. Headings that refer to an element or attribute use the <a
href="https://en.wikipedia.org/wiki/XPath">XPath</a> notation. Thus, for
instance, `/TEI/teiHeader` refers to the part in red in the following, and
`//body` refers to the part in orange:

<pre>
&lt;TEI&gt;
	<span style="color:red">&lt;teiHeader&gt;
		&lt;fileDesc&gt;
			Hello
		&lt;/fileDesc&gt;
	&lt;/teiHeader&gt;</span>
	&lt;text&gt;
		<span style="color:orange">&lt;body&gt;
			Some text
		&lt;/body&gt;</span>
	&lt;/text&gt;
&lt;/TEI>
</pre>

## Bibliography

### Referencing entries

For referencing bibliographic entries, as in `<ptr
target="bib:Nakacami1972_01"/>`, you should use the entries' short title as
key. Tags were used at some point, despite what the Zotero guide says, but this
is no longer allowed.

We use short titles as lookup keys for historical reasons, but they are not
meant for this purpose. Zotero does not check whether short titles are uniques
within the bibliography. Thus, we have many entries that bear the same short
title. Unfortunately, there is no way to address this without moving away from
the interface we are using. If the short title you are using is not unique, the
display interface will show this.

### Rich text formatting

Zotero allows <a
href="https://www.zotero.org/support/kb/rich_text_bibliography">rich text
formatting</a> with a few HTML tags, as follows:

* `<i>italics</i>` produces <i>italics</i>
* `<b>bold</b>` produces <b>bold</b>
* `<sub>subscript</sub>` produces <sub>subscript</sub>
* `<sup>superscript</sup>` produces <sup>superscript</sup>
* `<span style="font-variant:small-caps;">smallcaps</span>` produces <span style="font-variant:small-caps">smallcaps</span>

There is also a tag `<span class="nocase">hello there</span>`, that is used to
suppress automatic capitalization. I do not perform any automatic
capitalization for now, so it does not have any effect yet.

In addition to the above tags, I added support for hyperlinks:

* `<a href="https://example.org">click here</a>` produces <a href="https://example.org">click here</a>.

All other tags are removed. Thus, for instance, `<p>hello</p> there` produces
just `hello there`. If you need support for fancier formatting, do tell me.

Since Zotero allows HTML tags, you need to remember to escape characters that
have a special meaning in XML. Use `&lt;` instead of `<`, `&gt;` instead of
`>`, and `&amp;` instead of `&`. Be careful, in particular, when mentioning
several authors and places, as in "Joe & Allen", "Berlin & Hamburg", etc.

I try to fix escaping issues, but this is not reliable and cannot be, so you
still need to be careful.

### Record types

Zotero defines [a variety of record
types](https://www.zotero.org/support/kb/item_types_and_fields). I only added
support for the most common ones, namely:

* book
* bookSection
* journalArticle
* report
* thesis

If you need another record type to be supported, do tell me.

### Record fields

When using URLs, you should never reference a document that is not readily
accessible. Don't reference documents that are behind a paywall (as in JSTOR)
or that can only be consulted by subscribing to a service (academia.edu,
sharedocs, etc.). Put the document on [archive.org](https://archive.org), or
send it to me if you do not know how.

For reprints, etc. the DHARMA Zotero guide says to fill the "Edition" field in
full words, as in "2nd edition". In practice, you can (and should) set it to a
roman number whenever possible. The value "2" will produce "2nd edition", the value
"3" will produce "3rd edition", etc.

## Hyphenation

I add hyphenation break points to the text within `<div type="edition">`. This
is mostly useful for texts that contain long compounds, etc. without editorial
hyphens.

This is done very roughly. Soft hyphens U+00AD are added after groups of
vowels, so that the text reflows on syllables. This is only done for relatively
long pieces of text. If a piece of text already contains one or more soft
hyphens, I assume it is manually hyphenated and do not attempt to hyphenate it
further.

## `@xml:lang`

The EGD prescribes to use a three-letters language code, optionally followed by
a four-letters script name, as in `tam-Latn`.

The schema restricts language codes to the ones that are most likely useful,
but in practice any two-letters or three-letters language code from the
relevant ISO standards will work.

Script codes are always ignored, because they are not used properly. Still, the
use of the `Latn` script name is enforced in the schema for all Indic
languages, to avoid a combinatorial explosion. It is ignored as well viz. it is
not taken to mean that the Latin script is used. I will either remove all
script codes or amend them eventually.

## `/TEI/teiHeader/fileDesc/titleStmt`

This element includes names of editors within `<editor>` or `<respStmt>`.
Whenever there is an explicit reference to a DHARMA member or to a VIAF page in
the `@ref` attribute, the person's name is pulled from the relevant external
source, and the name given in the file is ignored. For instance, given this:

~~~
<respStmt>
	<resp>intellectual authorship of edition</resp>
	<persName ref="part:argr">
		<forename>John</forename>
		<surname>Doe</surname>
	</persName>
</respStmt>
~~~

... the name "John Doe" is ignored and replaced with "Arlo Griffiths"
(part:argr).

There are no conventions that would allow me to distinguish people's role, so
all people mentioned in this element are assumed to be editors, regardless of
what `<resp>` contains. If you need to distinguish several roles, say,
"editor", "collaborator", etc., bring this to the attention of the guides'
authors.

In the [catalog display](/catalog) and when displaying editions, person names
are enumerated in the order they appear within the file, so you might want to
add the names of the most important contributors at the top.

## `/TEI/teiHeader/fileDesc/publicationStmt`

This element contains boilerplate data that can easily be generated, e.g.:

	<publicationStmt>
		<authority>DHARMA</authority>
		<pubPlace>Paris</pubPlace>
		<idno type="filename">DHARMA_INSCIC00013</idno>
		<availability>
		<licence target="https://creativecommons.org/licenses/by/4.0/">
			<p>This work is licensed under the Creative Commons Attribution 4.0 Unported
			Licence. To view a copy of the licence, visit
			https://creativecommons.org/licenses/by/4.0/ or send a letter to
			Creative Commons, 444 Castro Street, Suite 900, Mountain View,
			California, 94041, USA.</p>
			<p>Copyright (c) 2019-2025 by Arlo Griffiths &amp; Salomé Pichon.</p>
		</licence>
	</availability>
	<date from="2019" to="2025">2019-2025</date>
	</publicationStmt>

The only element you need to fill properly is `<pubPlace>`. All other elements
will be deleted and regenerated with a template. In particular, don't bother to
edit the copyright license.

## `/TEI/teiHeader/fileDesc/sourceDesc`

Everything is ignored, except `./msDesc/physDesc/handDesc`.

## `/TEI/teiHeader/revisionDesc`

This element holds a revision history:

	<revisionDesc>
		<change who="part:sapi" when="2021-02-17" status="draft">Adding translation</change>
		<change who="part:sapi" when="2021-02-16" status="draft">Beggining initial encoding of the inscription</change>
	</revisionDesc>

It is of dubious interest nowadays, but is mandated by TEI. You do not need to
fill it regularly, since the revision history is tracked by git and could be
pulled from it, if needed.

## `//choice`

When a `<choice>` element contains several `<unclear>` elements, the first one
is deemed to be the most likely. Only this reading will be made searchable.
Thus for instance, if you have:

	X<choice>
		<unclear>A</unclear>
		<unclear>B</unclear>
		<unclear>C</unclear>
	</choice>Y

... the reading XAY will be made searchable, but not XBY nor XCY. For this
reason, you want to give the most probable reading first.




</div>
