% extends "base.tpl"

% block title
Editorial Conventions
% endblock

% block body

% for title, items in data:
<h2>{{title}}</h2>

<div class="catalog-list">
% for item in items:
<div class="catalog-card">
% if item.description:
<p class="catalog-card-heading">{{item.description}}</p>
% endif
<pre class="xml">
{{item.markup}}
</pre>
<div class="ed {{item.type == "edition" and "full" or "translation"}} edition-demo">
	{{item.block.render_full() | safe}}
</div>
% if item.remark:
	{{item.remark}}
% endif
</div>
% endfor
</div>

% endfor


</div>

% endblock
