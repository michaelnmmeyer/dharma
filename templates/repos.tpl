% extends "base.tpl"

% block title
Repositories
% endblock

% block body

<h1>Repositories</h1>

<div class="catalog-list">
% for repo in rows:
<div class="catalog-card">
<p>
	<b>{{repo["title"]}}</b>
% if repo["repo_prod"] is not none:
	({{repo["repo_prod"]}} texts)
% endif
</p>
% if repo["people"]:
<p>Editors:
% for editor, prod in from_json(repo["people"]):
{{editor}} ({{prod}}){{loop.index == loop.length and "." or ","}}
% endfor
</p>
% endif
% if repo["langs"]:
<p>Languages:
% for lang, prod in from_json(repo["langs"]):
{{lang}} ({{prod}}){{loop.index == loop.length and "." or ","}}
% endfor
</p>
% endif
<p><span class="repo-id">{{repo["repo"]}}</span></p>
</div> <!-- class="catalog-card" -->
% endfor
</div> <!-- class="catalog-list" -->

% endblock
