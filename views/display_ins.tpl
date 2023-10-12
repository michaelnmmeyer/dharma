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
% for section in doc.edition:
% if section.heading:
<h3 class="dh-ed-heading">{{!section.heading.render_logical()}}</h3>
% end
<div class="dh-ed-section">
   {{!section.contents.render_logical()}}
</div>
% end
</div>

<div class="dh-phys" id="dh-phys" style="display:none">
% for section in doc.edition:
% if section.heading:
<h3 class="dh-ed-heading">{{!section.heading.render_physical()}}</h3>
% end
<div class="dh-ed-section">
   {{!section.contents.render_physical()}}
</div>
% end
</div>

</div> <!-- <div class="body"> -->

<div class="dh-xml" id="dh-xml" style="display:none">
<pre>
{{!doc.xml}}
</pre>
</div>
