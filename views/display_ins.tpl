% rebase("base.tpl", title="Display", includes='''
   <link rel="stylesheet" href="/ins-common.css">
	<link rel="stylesheet" href="/ins-phys.css" id="ins-display">
	<script type="text/javascript" src="/ins.js"></script>
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
   <button id="phys-btn">Physical</button>
   <button id="log-btn">Logical</button>
   <button id="xml-btn">XML</button>
</div>

<div class="dh-ed">

% for section in doc.edition:

% if section.heading:
<h3 class="dh-ed-heading">{{!section.heading.render()}}</h3>
% end

<div class="dh-ed-section">
   {{!section.contents.render()}}
</div>

% end

</div>
</div>

<div class="dh-xml">
<pre>
{{doc.xml}}
</pre>
</div>
