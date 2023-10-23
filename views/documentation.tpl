<!--
% rebase("base.tpl", title="Documentation")
-->
<div class="body">
<h1>
Documentation
</h1>
<p>You can consult here the TEI documentation generated from DHARMA
schemas. You should follow this instead of the documentation on the TEI
website, because our schemas are more restrictive. Even so, they are
more permissive than they should.</p>
<p>We currently have four schemas. The schema used to validate a given
text is inferred from the file name. Processing instructions at the
beginning of the file are ignored.</p>
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
<p>Encoded texts generally deviate from the guidelines, and it is
unreasonable to expect people to come back to them again and again, as I
discover new issues. Thus, I try to do something sensible whenever
possible viz. whenever something can be mechanically inferred.</p>
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
<p>This is done very roughly. Soft hyphens are added after groups of
vowels, so that the text reflows on syllables. This is only done for
relatively long pieces of text. If a piece of text already contains one
or more soft hyphens, I assume it is manually hyphenated and do not
attempt to hyphenate it.</p>
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
