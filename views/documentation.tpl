<!--
% rebase("base.tpl", title="Documentation")
-->
<div class="body">
<h1>
Documentation
</h1>
<p>You can consult here the TEI documentation generated from DHARMA
schemas. You should consult this instead of the documentation on the TEI
website, because our schemas are more restrictive. Even so, they are
more permissive than they should.</p>
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
<p>Here are a few notes on how XML files are interpreted. Headings
indicate the element location in XPath notation. Thus, for instance,
/TEI/teiHeader refers to STUFF in the following:</p>
<pre><code>&lt;TEI&gt;
    &lt;teiHeader&gt;STUFF&lt;/teiHeader&gt;
&lt;/TEI&gt;</code></pre>
<h2
id="teiteiheaderfiledesctitlestmt">/TEI/teiHeader/fileDesc/titleStmt</h2>
<p>This element includes names of editors within
<code>&lt;editor&gt;</code> or <code>&lt;respStmt&gt;</code>. Whenever
there is an explicit reference to a DHARMA member or to a VIAF page, the
person’s name is pulled from the relevant external source, and the name
given in the file is ignored. For instance, given this:</p>
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
role, so all people mentioned in this element are assumed to be editors.
They are enumerated in the order they appear within the file, so you
might want to add the names of the most important contributors at the
top.</p>
<h2
id="teiteiheaderfiledescpublicationstmt">/TEI/teiHeader/fileDesc/publicationStmt</h2>
<p>Everything under here is ignored, except
<code>&lt;pubPlace&gt;</code>.</p>
</div>
