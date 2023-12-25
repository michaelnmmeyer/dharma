<!--
% rebase("base.tpl", title="Documentation")
-->
<div class="body">
<h1>
Documentation
</h1>
<p>This is a complement to the various guides of the project. It
addresses some issues that are not covered by the guides, and points out
how I deviate from the guidelines, when I do deviate from them.</p>
<p>Encoded texts generally deviate from the guidelines, and it is
unreasonable to expect people to come back to them again and again, as I
discover new issues. Thus, I try to do something sensible whenever
possible viz. whenever something can be mechanically inferred.</p>
<h2 id="how-files-are-pulled-and-validated">How files are pulled and
validated</h2>
<p>The DHARMA app is hooked to Github and updates its database whenever
you push to a repository. To determine which files should be added to
the database, it looks at their filenames. XML Files whose name starts
with <code>DHARMA_INS</code>, <code>DHARMA_DiplEd</code> or
<code>DHARMA_CritEd</code> are deemed to be texts, unless they contain
the word “template” (whatever the capitalization of this word).</p>
<p>The location of texts in the repository does not matter. You can put
them in different directories if needed. If you want a text you are
editing not to be indexed, use another naming convention,
e.g. <code>XDHARMA_INS</code>, etc.</p>
<p>The schema used to validate a given text is derived from the file
name. The DHARMA app does not look at processing instructions at the
beginning of XML files, e.g.:</p>
<pre><code>&lt;?xml-model href=&quot;https://raw.githubusercontent.com/erc-dharma/project-documentation/master/schema/latest/DHARMA_Schema.rng&quot; type=&quot;application/xml&quot; schematypens=&quot;http://relaxng.org/ns/structure/1.0&quot;?&gt;
&lt;?xml-model href=&quot;https://raw.githubusercontent.com/erc-dharma/project-documentation/master/schema/latest/DHARMA_Schema.rng&quot; type=&quot;application/xml&quot; schematypens=&quot;http://purl.oclc.org/dsdl/schematron&quot;?&gt;
&lt;?xml-model href=&quot;https://raw.githubusercontent.com/erc-dharma/project-documentation/master/schema/latest/DHARMA_SQF.sch&quot; type=&quot;application/xml&quot; schematypens=&quot;http://purl.oclc.org/dsdl/schematron&quot;?&gt;
&lt;?xml-model href=&quot;https://epidoc.stoa.org/schema/latest/tei-epidoc.rng&quot; schematypens=&quot;http://relaxng.org/ns/structure/1.0&quot;?&gt;
&lt;?xml-model href=&quot;https://epidoc.stoa.org/schema/latest/tei-epidoc.rng&quot; schematypens=&quot;http://purl.oclc.org/dsdl/schematron&quot;?&gt;</code></pre>
<p>These instructions are interpreted by Oxygen, however.</p>
<h2 id="dharma-schemas">DHARMA Schemas</h2>
<p>Here is the TEI documentation generated from DHARMA schemas. You
should follow this instead of the <a
href="https://www.tei-c.org/release/doc/tei-p5-doc/en/html/index.html">documentation
on the TEI website</a>, because our schemas are more restrictive. Even
so, they are often more permissive than they should: if your file
validates, this does not necessarily mean that it is valid.</p>
<ul>
<li>
<a href="/documentation/inscription">Inscriptions</a> (files named
DHARMA_INS*)
</li>
<li>
<a href="/documentation/diplomatic">Diplomatic editions</a> (files named
DHARMA_DiplEd*)
</li>
<li>
<a href="/documentation/critical">Critical editions</a> (files named
DHARMA_CritEd*)
</li>
<li>
<a href="/documentation/bestow">BESTOW</a> (no file naming convention)
</li>
</ul>
<h2 id="bibliography">Bibliography</h2>
<p>Our bibliography is stored on Zotero servers <a
href="https://www.zotero.org/groups/1633743/erc-dharma">here</a>. The
DHARMA database stores a copy of it, which is updated every hour or so,
but not immediately after a modification (for now).</p>
<p>It is important to know that, even though we are using the Zotero
data model, we are using several distinct bibliography processors for
formatting entries and references. They do not necessarily produce the
same result. There are three main processors:</p>
<ul>
<li>A processor written by the Zotero team, which is used by the Zotero
app installed on your computer, when e.g. you add citations in Word.
This processor works with CSL stylesheets. We have two such custom
stylesheets in <a
href="https://github.com/erc-dharma/project-documentation/tree/master/bibliography">project-documentation/bibliography</a>.</li>
<li>A processor Axelle wrote. It is used on the static website, <a
href="https://erc-dharma.github.io">erc-dharma.github.io</a>.</li>
<li>A processor I (Michaël) wrote. It is used on the new website, <a
href="https://dharman.in">dharman.in</a>.</li>
</ul>
<h3 id="referencing-entries">Referencing entries</h3>
<p>For referencing bibliographic entries, as in
<code>&lt;ptr target="bib:Nakacami1972_01"/&gt;</code>, you should use
the entries’ short title as key. Tags were used at some point, despite
what the Zotero guide says, but this is no longer allowed.</p>
<p>We use short titles as lookup keys for historical reasons, but they
are not meant for this purpose. Zotero does not check whether short
titles are uniques within the bibliography. Thus, we have many entries
that bear the same short title. Unfortunately, there is no way to
address this without moving away from the interface we are using. If the
short title you are using is not unique, the display interface will show
this.</p>
<h3 id="rich-text-formatting">Rich text formatting</h3>
<p>Zotero allows <a
href="https://www.zotero.org/support/kb/rich_text_bibliography">rich
text formatting</a> with a few HTML tags, as follows:</p>
<ul>
<li><code>&lt;i&gt;italics&lt;/i&gt;</code> produces <i>italics</i></li>
<li><code>&lt;b&gt;bold&lt;/b&gt;</code> produces <b>bold</b></li>
<li><code>&lt;sub&gt;subscript&lt;/sub&gt;</code> produces
<sub>subscript</sub></li>
<li><code>&lt;sup&gt;superscript&lt;/sup&gt;</code> produces
<sup>superscript</sup></li>
<li><code>&lt;span style="font-variant:small-caps;"&gt;Smallcaps&lt;/span&gt;</code>
produces <span class="smallcaps">Smallcaps</span></li>
</ul>
<p>There is also a tag
<code>&lt;span class="nocase"&gt;hello there&lt;/span&gt;</code>, that
is used to suppress automatic capitalization. I do not perform any
automatic capitalization for now, so it does not have any effect
yet.</p>
<p>In addition to the above tags, I added support for hyperlinks:</p>
<ul>
<li><code>&lt;a href="https://example.org"&gt;click here&lt;/a&gt;</code>
produces <a href="https://example.org">click here</a>.</li>
</ul>
<p>All other tags are removed. Thus, for instance,
<code>&lt;p&gt;hello&lt;/p&gt; there</code> produces just
<code>hello there</code>. If you need support for fancier formatting, do
tell me.</p>
<p>Since Zotero allows HTML tags, you need to remember to escape
characters that have a special meaning in XML. Use <code>&amp;lt;</code>
instead of <code>&lt;</code>, <code>&amp;gt;</code> instead of
<code>&gt;</code>, and <code>&amp;amp;</code> instead of
<code>&amp;</code>. Be careful, in particular, when mentioning several
authors and places, as in “Joe &amp; Allen”, “Berlin &amp; Hamburg”,
etc.</p>
<p>I try to fix escaping issues, but this is not reliable and cannot be,
so you still need to be careful.</p>
<h3 id="record-types">Record types</h3>
<p>Zotero defines <a
href="https://www.zotero.org/support/kb/item_types_and_fields">a variety
of record types</a>. I only added support for the most common ones,
namely:</p>
<ul>
<li>book</li>
<li>bookSection</li>
<li>conferencePaper</li>
<li>journalArticle</li>
<li>report</li>
<li>thesis</li>
<li>webpage</li>
</ul>
<p>If you need another record type to be supported, do tell me.</p>
<h3 id="record-fields">Record fields</h3>
<dl>
<dt>
date
</dt>
<dd>
The guide prescribes to use “n.d.” when there is no date. You can leave
this field empty, the correct output will be generated anyway.
</dd>
<dt>
edition
</dt>
<dd>
For reprints, etc. the DHARMA Zotero guide says to fill this field in
full words, as in “2nd edition”. In practice, you can just set it to a
Roman number. The value “2” will produce “2nd edition”, the value “3”
will produce “3rd edition”, etc.
</dd>
<dt>
extra
</dt>
<dd>
This field is almost always filled with junk generated when importing
bibliographies, so I ignore it completely.
</dd>
<dt>
publisher
</dt>
<dd>
The guide prescribes to use “n.pub” when there is no publisher. You can
leave this field empty, the correct output will be generated anyway.
</dd>
<dt>
URL
</dt>
<dd>
<p>Most URLs I have seen so far in this field are unusable, so I never
display them unless they are absolutely necessary for locating the
document. For now, they are only shown when the record type is “report”
or “webpage”.</p>
<p>When using URLs, you should never reference a document that is not
readily accessible. Don’t reference documents that are behind a paywall
(JSTOR, Brill, etc.) or that can only be consulted by subscribing to a
service (academia.edu, sharedocs, etc.). Put the document on <a
href="https://hal.science">HAL</a> or on <a
href="https://archive.org">archive.org</a>.</p>
For the rare cases you need to specify several URLs in the URL field,
the EGD prescribes to delimit them with a semicolon. But semicolons (as
well as commas, etc.) can and do appear in URLs, which makes them
ambiguous. Delimit URLs with whitespace instead.
</dd>
</dl>
<h2 id="xml-files-interpretation">XML files interpretation</h2>
<p>Here are a few notes on how XML files are interpreted. This only
concerns inscriptions for now. Headings that refer to an element or
attribute use the <a
href="https://en.wikipedia.org/wiki/XPath">XPath</a> notation. Thus, for
instance, <code>/TEI/teiHeader</code> refers to the part in red in the
following, and <code>//body</code> refers to the part in orange:</p>
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
<h2 id="hyphenation">Hyphenation</h2>
<p>I add hyphenation break points to the text within
<code>&lt;div type="edition"&gt;</code>. This is mostly useful for texts
that contain long compounds, etc. without editorial hyphens.</p>
<p>This is done very roughly. Soft hyphens U+00AD are added after groups
of vowels, so that the text reflows on syllables. This is only done for
relatively long pieces of text. If a piece of text already contains one
or more soft hyphens, I assume it is manually hyphenated and do not
attempt to hyphenate it further.</p>
<h2 id="xmllang"><code>@xml:lang</code></h2>
<p>The EGD prescribes to use a three-letters language code, optionally
followed by a four-letters script name, as in <code>tam-Latn</code>.</p>
<p>The schema restricts language codes to the ones that are most likely
useful, but in practice any two-letters or three-letters language code
from the relevant ISO standards will work.</p>
<p>Script codes are always ignored, because they are not used properly.
Still, the use of the <code>Latn</code> script name is enforced in the
schema for all Indic languages, to avoid a combinatorial explosion. It
is ignored as well viz. it is not taken to mean that the Latin script is
used. I will either remove all script codes or amend them
eventually.</p>
<h2
id="teiteiheaderfiledesctitlestmt"><code>/TEI/teiHeader/fileDesc/titleStmt</code></h2>
<p>This element includes names of editors within
<code>&lt;editor&gt;</code> or <code>&lt;respStmt&gt;</code>. Whenever
there is an explicit reference to a DHARMA member or to a VIAF page in
the <code>@ref</code> attribute, the person’s name is pulled from the
relevant external source, and the name given in the file is ignored. For
instance, given this:</p>
<pre><code>&lt;respStmt&gt;
    &lt;resp&gt;intellectual authorship of edition&lt;/resp&gt;
    &lt;persName ref=&quot;part:argr&quot;&gt;
        &lt;forename&gt;John&lt;/forename&gt;
        &lt;surname&gt;Doe&lt;/surname&gt;
    &lt;/persName&gt;
&lt;/respStmt&gt;</code></pre>
<p>… the name “John Doe” is ignored and replaced with “Arlo Griffiths”
(part:argr).</p>
<p>There are no conventions that would allow me to distinguish people’s
role, so all people mentioned in this element are assumed to be editors,
regardless of what <code>&lt;resp&gt;</code> contains. If you need to
distinguish several roles, say, “editor”, “collaborator”, etc., bring
this to the attention of the guides’ authors.</p>
<p>In the <a href="/catalog">catalog display</a> and when displaying
editions, person names are enumerated in the order they appear within
the file, so you might want to add the names of the most important
contributors at the top.</p>
<h2
id="teiteiheaderfiledescpublicationstmt"><code>/TEI/teiHeader/fileDesc/publicationStmt</code></h2>
<p>This element contains boilerplate data that can easily be generated,
e.g.:</p>
<pre><code>&lt;publicationStmt&gt;
    &lt;authority&gt;DHARMA&lt;/authority&gt;
    &lt;pubPlace&gt;Paris&lt;/pubPlace&gt;
    &lt;idno type=&quot;filename&quot;&gt;DHARMA_INSCIC00013&lt;/idno&gt;
    &lt;availability&gt;
    &lt;licence target=&quot;https://creativecommons.org/licenses/by/4.0/&quot;&gt;
        &lt;p&gt;This work is licensed under the Creative Commons Attribution 4.0 Unported
        Licence. To view a copy of the licence, visit
        https://creativecommons.org/licenses/by/4.0/ or send a letter to
        Creative Commons, 444 Castro Street, Suite 900, Mountain View,
        California, 94041, USA.&lt;/p&gt;
        &lt;p&gt;Copyright (c) 2019-2025 by Arlo Griffiths &amp;amp; Salomé Pichon.&lt;/p&gt;
    &lt;/licence&gt;
&lt;/availability&gt;
&lt;date from=&quot;2019&quot; to=&quot;2025&quot;&gt;2019-2025&lt;/date&gt;
&lt;/publicationStmt&gt;</code></pre>
<p>The only element you need to fill properly is
<code>&lt;pubPlace&gt;</code>. All other elements will be deleted and
regenerated with a template. In particular, don’t bother to edit the
copyright license.</p>
<h2
id="teiteiheaderfiledescsourcedesc"><code>/TEI/teiHeader/fileDesc/sourceDesc</code></h2>
<p>Everything is ignored, except
<code>./msDesc/physDesc/handDesc</code>.</p>
<h2
id="teiteiheaderrevisiondesc"><code>/TEI/teiHeader/revisionDesc</code></h2>
<p>This element holds a revision history:</p>
<pre><code>&lt;revisionDesc&gt;
    &lt;change who=&quot;part:sapi&quot; when=&quot;2021-02-17&quot; status=&quot;draft&quot;&gt;Adding translation&lt;/change&gt;
    &lt;change who=&quot;part:sapi&quot; when=&quot;2021-02-16&quot; status=&quot;draft&quot;&gt;Beggining initial encoding of the inscription&lt;/change&gt;
&lt;/revisionDesc&gt;</code></pre>
<p>It is of dubious interest nowadays, but is mandated by TEI. You do
not need to fill it regularly, since the revision history is tracked by
git and could be pulled from it, if needed.</p>
<h2 id="choice"><code>//choice</code></h2>
<p>When a <code>&lt;choice&gt;</code> element contains several
<code>&lt;unclear&gt;</code> elements, the first one is deemed to be the
most likely. Only this reading will be made searchable. Thus for
instance, if you have:</p>
<pre><code>X&lt;choice&gt;
    &lt;unclear&gt;A&lt;/unclear&gt;
    &lt;unclear&gt;B&lt;/unclear&gt;
    &lt;unclear&gt;C&lt;/unclear&gt;
&lt;/choice&gt;Y</code></pre>
<p>… the reading XAY will be made searchable, but not XBY nor XCY. For
this reason, you want to give the most probable reading first.</p>
</div>
