% extends "base.tpl"

% block title
Repositories
% endblock

% block body

<h1>Repositories</h1>

<div class="catalog-list">
% for repo in rows:
<div class="catalog-card">
<p><b>{{repo["title"]}}</b> ({{repo["repo_prod"]}})</p>
<p>Editors:
% for i, (editor, count) in enumerate(json.loads(repo["people"])):
{{editor}} ({{count}}){{i == loop.length - 1 and "." or ","}}
% endfor
</p>
<p><span class="repo-id">{{repo["name"]}}</span></p>
</div> <!-- class="catalog-card" -->
% endfor
</div> <!-- class="catalog-list" -->

% endblock
