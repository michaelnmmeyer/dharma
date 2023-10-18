% rebase("base.tpl", title="Display", includes='''
   <link rel="stylesheet" href="/inscription.css">
	<script type="text/javascript" src="/inscription.js"></script>
''')

<div class="body">
<h1>{{text.removeprefix("DHARMA_")}}</h1>

<h2>
% for part in doc.title:
   {{!part}}.
% end
</h2>

<p>
{{numberize("Editor", len(doc.editors))}}:
% for ed in doc.editors[:-1]:
   {{!ed}},
% end
% if doc.editors:
   {{!doc.editors[-1]}}.
% else:
   Unknown.
% end
</p>

<div>
   <button id="log-btn">Logical</button>
   <button id="phys-btn">Physical</button>
   <button id="xml-btn">XML</button>
</div>

<div class="dh-log" id="dh-log">
<h3>Edition (logical)</h3>
{{!doc.edition.render_logical()}}
</div>

<div class="dh-phys" id="dh-phys" style="display:none">
<h3>Edition (physical)</h3>
{{!doc.edition.render_physical()}}
</div>

</div> <!-- <div class="body"> -->

<div class="dh-xml" id="dh-xml" style="display:none">
<pre>
{{!doc.xml}}
</pre>
</div>

<div class="body">

% for trans in doc.translation:
<div class="dh-trans">
<h3>Translation</h3>
{{!trans.render_logical()}}
</div>
% end

% if doc.commentary:
<div class="dh-trans">
<h3>Commentary</h3>
{{!doc.commentary.render_logical()}}
</div>
% end

</div> <!-- <div class="body"> -->
