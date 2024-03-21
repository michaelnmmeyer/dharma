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
% if repo["repo_prod"] is not none:
	<b><a href="{{url_for('show_catalog', q='repo:' + repo['repo'])}}">{{repo["title"]}}</a></b>
	({{repo["repo_prod"]}} texts)
% else:
	<b>{{repo["title"]}}</b>
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
<p><a href="https://github.com/erc-dharma/{{format_url(repo['repo'])}}"><i class="fa-brands fa-github"></i> <span class="repo-id">{{repo["repo"]}}</span></a></p>
</div> <!-- class="catalog-card" -->
% endfor
</div> <!-- class="catalog-list" -->

% endblock
