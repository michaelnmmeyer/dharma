% extends "base.tpl"

% block title
Repositories
% endblock

% block body

<h1>Repositories</h1>

<p>Most of our git repositories are hosted <a
href="https://github.com/erc-dharma">here</a>. The table below does not show all
of them; in particular, it does not show private repositories.</p>

<div class="catalog-list">

% for repo in rows:
<div class="catalog-card">
<p>
	<b>{{repo["title"]}}</b>
% if repo["repo_prod"] is not none:
	(<a href="{{url_for('show_catalog', q='repo:' + repo['repo'])}}">{{repo["repo_prod"]}} {{numberize("text", repo["repo_prod"])}}</a>)
% endif
</p>
% if repo["people"]:
<p>Editors:
% for editor_id, editor, prod in from_json(repo["people"]):
{{editor}}
(<a href="{{url_for('show_catalog', q='repo:%s editor_id:%s' % (repo["repo"], editor_id))}}">{{prod}}</a>){{loop.index == loop.length and "." or ","}}
% endfor
</p>
% endif
% if repo["langs"]:
<p>Languages:
% for lang_id, lang, prod in from_json(repo["langs"]):
{{lang}}
(<a href="{{url_for('show_catalog', q='repo:%s lang:%s' % (repo["repo"], lang_id))}}">{{prod}}</a>){{loop.index == loop.length and "." or ","}}
% endfor
</p>
% endif
<p><a href="https://github.com/erc-dharma/{{format_url(repo['repo'])}}"><i class="fa-brands fa-github"></i> <span class="repo-id">{{repo["repo"]}}</span></a></p>
% if repo["commit_hash"]:
<p>
Last updated {{repo["commit_date"] | format_date}}
(<a href="https://github.com/erc-dharma/{{repo['repo']}}/commit/{{repo['commit_hash']}}"><span class="commit-hash">{{repo["commit_hash"][:7]}}</span></a>)
<i class="fa-regular fa-circle-question" data-tip="This is the latest commit
processed by the DHARMA application. The repository might contain more recent
commits."></i>
</p>
% endif
</div> <!-- class="catalog-card" -->

% endfor
</div> <!-- class="catalog-list" -->

% endblock
