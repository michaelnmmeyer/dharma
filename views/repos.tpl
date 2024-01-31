% rebase("base.tpl", title="Repositories")

<div class="body">
<h1>Repositories</h1>

<div class="catalog-list">
% for repo in rows:
<div class="catalog-card">
<p><b>{{repo["title"]}}</b> ({{repo["repo_prod"]}})</p>
<p>Editors:
% people = json.loads(repo["people"])
% for i, (editor, count) in enumerate(people):
{{editor}} ({{count}}){{i == len(people) - 1 and "." or ","}}
% end
</p>
<p><span class="text-id">{{repo["name"]}}</span></p>

</div>
