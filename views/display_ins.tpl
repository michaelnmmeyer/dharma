% rebase("base.tpl", title="Display", includes='''
   <link rel="stylesheet" href="/ins-common.css">
	<link rel="stylesheet" href="/ins-phys.css" id="ins-display">
	<script type="text/javascript" src="/ins.js"></script>
''')

<div class="body">
<h1>{{text.removeprefix("DHARMA_")}}</h1>

<button id="phys-btn">Physical</button>
<button id="log-btn">Logical</button>

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
