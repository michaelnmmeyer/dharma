<!--
% rebase("base.tpl", title="Documentation")
-->

<div class="body">
<h1>Documentation</h1>

You can consult here the TEI documentation generated from DHARMA
schemas. You should follow this instead of the documentation on the TEI
website, because our schemas are more restrictive. Even so, they are more
permissive than they should.

We currently have four schemas. The schema used to validate a given text is
inferred from the file name. Processing instructions at the beginning of the
file are ignored.

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
inscriptions for now. Headings indicate the element location in <a
href="https://en.wikipedia.org/wiki/XPath">XPath</a> notation.
Thus, for instance, `/TEI/teiHeader` refers to the part in red in the
following, and `//body` refers to the part in orange:

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
