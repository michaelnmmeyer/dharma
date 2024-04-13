% extends "base.tpl"

% block title
Editorial Conventions
% endblock

% block body

% for title, items in data:
<h2>{{title}}</h2>

<div class="card-list">

% for item in items:
<div class="card">

% if item.description:
<div class="card-heading">{{item.description}}</div>
% endif

<div class="card-body">
<div class="edition-demo">
	<pre class="xml">{{item.markup}}</pre>
	<div class="ed {{item.type == "edition" and "full" or "translation"}}">
	{{item.block.render_full() | safe}}
	</div>
</div><!--class="edition-demo"-->
% if item.remark:
	<p>{{item.remark}}</p>
% endif
</div><!--class="card-body"-->

</div><!--class="card"-->
% endfor

</div><!--class="card-list"-->
% endfor

% endblock
