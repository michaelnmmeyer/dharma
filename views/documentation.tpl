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
concerns inscriptions for now. Headings indicate the element location in
<a
href="https://en.wikipedia.org/wiki/XPath">XPath</a> notation. Thus, for
instance, <code>/TEI/teiHeader</code> refers to the part in red in the
following:</p>
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
<h2 id="xmllang"><code>@xml:lang</code></h2>
<p>The EGD prescribes to use a three-letters language code, optionally
followed by a four-letters script name.</p>
<p>The schema restricts language codes to the ones that are most likely
useful, but in practice you can use any two-letters or three-letters
language code from the relevant ISO standards.</p>
<p>In practice, people don’t tag script names correctly, so the script
name is always ignored. The use of the <code>Latn</code> script name is
enforced in the schema for all Indic languages to avoid a combinatorial
explosion. It is ignored as well viz. it is not taken to mean that the
Latin script is used.</p>
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
regardless of what <code>&lt;resp&gt;</code> contains.</p>
<p>Person names are enumerated in the order they appear within the file,
so you might want to add the names of the most important contributors at
the top.</p>
<h2
id="teiteiheaderfiledescpublicationstmt"><code>/TEI/teiHeader/fileDesc/publicationStmt</code></h2>
<p>Everything under here is ignored, except
<code>&lt;pubPlace&gt;</code>.</p>
<h2
id="teiteiheaderfiledescsourcedesc"><code>/TEI/teiHeader/fileDesc/sourceDesc</code></h2>
<p>Everything is ignored, except
<code>./msDesc/physDesc/handDesc</code>.</p>
<h2
id="teiteiheaderrevisiondesc"><code>/TEI/teiHeader/revisionDesc</code></h2>
<p>Everything under here is ignored. It is pointless to fill it, since
the revision history is tracked by git and could be pulled from it, if
needed.</p>
</div>
