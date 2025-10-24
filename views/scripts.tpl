% extends "base.tpl"

% block title
Scripts
% endblock

% block body

<p>The following only displays scripts that currently appear in the DHARMA database.</p>

<div class="catalog-list">

% for row in rows:
<div id="script-{{row['script']}}" class="catalog-card">

<p>
	<b>{{row["name"]}}</b> [<span class="monospace">{{row["script"]}}</span>]
% if row["prod"] is not none:
	(<a href="{{url_for('show_catalog', q='script:' + row['script'])}}">{{row["prod"]}} {{numberize("text", row["prod"])}}</a>)
% endif
</p>

% if row["repos"]:
<p>
Repositories:
% for repo, repo_prod in from_json(row["repos"]):
   <span class="repo-id">{{repo}}</span>
   (<a href="{{url_for('show_catalog', q='script:%s repo:%s' % (row["script"], repo))}}">{{repo_prod}}</a>){{loop.index == loop.length and "." or ","}}
% endfor
</p>
% endif

% if row["editors"]:
<p>
Editors:
% for editor_id, editor, editor_prod in from_json(row["editors"]):
   {{editor}}
   (<a href="{{url_for('show_catalog', q='script:%s editor_id:%s' % (row["script"], editor_id))}}">{{editor_prod}}</a>){{loop.index == loop.length and "." or ","}}
% endfor
</p>
% endif

<p>Standard: {{row["standard"]}}.</p>

</div>
% endfor

</div> <!-- class="catalog-list" -->

% endblock
