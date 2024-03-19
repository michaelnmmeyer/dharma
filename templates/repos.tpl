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
% for editor, count in from_json(repo["people"]):
{{editor}} ({{count}}){{loop.index == loop.length - 1 and "." or ","}}
% endfor
</p>
<p><span class="repo-id">{{repo["name"]}}</span></p>
</div> <!-- class="catalog-card" -->
% endfor
</div> <!-- class="catalog-list" -->

% endblock
