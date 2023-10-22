% rebase("base.tpl", title="Display", includes='''
   <link rel="stylesheet" href="/inscription.css">
	<script type="text/javascript" src="/inscription.js"></script>
''')

<div class="body">

<h1>
% for part in doc.title:
   {{!part}}.
% end
</h1>

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
<p>
Identifier: {{text.removeprefix("DHARMA_")}}
</p>

<div class="dh-ed">

<h2>Edition</h2>

<ul class="dh-ed-tabs">
   <li id="log-btn" class="dh-active"><a href="#dh-ed">Logical</a></li>
   <li id="phys-btn"><a href="#dh-ed">Physical</a></li>
   <li id="xml-btn"><a href="#dh-ed">XML</a></li>
</ul>

<div class="dh-log" id="dh-log">
{{!doc.edition.render_logical()}}
</div>

<div class="dh-phys" id="dh-phys" style="display:none">
{{!doc.edition.render_physical()}}
</div>

</div> <!-- <div class="dh-ed"> -->

</div> <!-- <div class="body"> -->

<div class="dh-xml" id="dh-xml" style="display:none">
<pre>
{{!doc.xml}}
</pre>
</div>

<div class="body">

% if doc.apparatus:
<div class="dh-apparatus">
<h2>Apparatus</h2>
{{!doc.apparatus.render_logical()}}
</div>
% end

% for trans in doc.translation:
<div class="dh-trans">
<h2>Translation</h2>
{{!trans.render_logical()}}
</div>
% end

% if doc.commentary:
<div class="dh-trans">
<h2>Commentary</h2>
{{!doc.commentary.render_logical()}}
</div>
% end

% if doc.bibliography:
<div class="dh-biblio">
<h2>Bibliography</h2>
{{!doc.bibliography.render_logical()}}
</div>
% end

</div> <!-- <div class="body"> -->
