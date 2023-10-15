<!--
% rebase("base.tpl", title="Documentation")
-->

<div class="body">
<h1>Documentation</h1>

You can consult here the TEI documentation generated from DHARMA
schemas. You should consult this instead of the documentation on the TEI
website, because our schemas are more restrictive. Even so, they are more
permissive than they should.

We currently have four schemas. The schema used to validate a given text is
inferred from the file name.

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

Here are a few notes on how XML files are interpreted. This only concerns
inscriptions for now. Headings indicate the element location in XPath notation.
Thus, for instance, `/TEI/teiHeader` refers to STUFF in the following:

	<TEI>
		<teiHeader>STUFF</teiHeader>
	</TEI>

## `/TEI/teiHeader/fileDesc/titleStmt`

This element includes names of editors within `<editor>` or `<respStmt>`.
Whenever there is an explicit reference to a DHARMA member or to a VIAF
page, the person's name is pulled from the relevant external source, and the
name given in the file is ignored. For instance, given this:

	<respStmt>
		<resp>intellectual authorship of edition</resp>
		<persName ref="part:argr">
			<forename>John</forename>
			<surname>Doe</surname>
		</persName>
	</respStmt>

... the name "John Doe" is ignored and replaced with "Arlo Griffiths"
(part:argr).

There are no conventions that would allow me to distinguish people's role, so all people
mentioned in this element are assumed to be editors. They are enumerated in
the order they appear within the file, so you might want to add the names of
the most important contributors at the top.

## `/TEI/teiHeader/fileDesc/publicationStmt`

Everything under here is ignored, except `<pubPlace>`.

## `/TEI/teiHeader/fileDesc/sourceDesc`

Everything is ignored, except `./msDesc/physDesc/handDesc`.

## `/TEI/teiHeader/revisionDesc`

Everything under here is ignored. It is pointless to fill it, since the revision history
is tracked by git and could be pulled from it, if needed.



</div>
