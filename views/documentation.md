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
Thus, for instance, `/TEI/teiHeader` refers to the part in red in the following:

<pre>
	&lt;TEI&gt;
		<span style="color:red">&lt;teiHeader&gt;
			&lt;fileDesc&gt;
				Hello
			&lt;/fileDesc&gt;
		&lt;/teiHeader&gt;</span>
		&lt;text&gt;
			&lt;body&gt;
				Some text
			&lt;/body&gt;
		&lt;/text&gt;
	&lt;/TEI>
</pre>

## `@xml:lang`

The EGD prescribes to use a three-letters language code, optionally followed by
a four-letters script name.

The schema restricts language codes to the ones that are most likely useful,
but in practice you can use any two-letters or three-letters language code from
the relevant ISO standards.

In practice, people don't tag script names correctly, so the script name is
always ignored. The use of the `Latn` script name is enforced in the schema for
all Indic languages to avoid a combinatorial explosion. It is ignored as well
viz. it is not taken to mean that the Latin script is used.

## `/TEI/teiHeader/fileDesc/titleStmt`

This element includes names of editors within `<editor>` or `<respStmt>`.
Whenever there is an explicit reference to a DHARMA member or to a VIAF page in
the `@ref` attribute, the person's name is pulled from the relevant external
source, and the name given in the file is ignored. For instance, given this:

	<respStmt>
		<resp>intellectual authorship of edition</resp>
		<persName ref="part:argr">
			<forename>John</forename>
			<surname>Doe</surname>
		</persName>
	</respStmt>

... the name "John Doe" is ignored and replaced with "Arlo Griffiths"
(part:argr).

There are no conventions that would allow me to distinguish people's role, so
all people mentioned in this element are assumed to be editors, regardless of
what `<resp>` contains.

Person names are enumerated in the order they appear within the file, so you
might want to add the names of the most important contributors at the top.

## `/TEI/teiHeader/fileDesc/publicationStmt`

Everything under here is ignored, except `<pubPlace>`.

## `/TEI/teiHeader/fileDesc/sourceDesc`

Everything is ignored, except `./msDesc/physDesc/handDesc`.

## `/TEI/teiHeader/revisionDesc`

Everything under here is ignored. It is not necessary to fill it, since the
revision history is tracked by git and could be pulled from it, if needed.

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
