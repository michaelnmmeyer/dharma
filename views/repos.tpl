% rebase("base.tpl", title="Repositories")

<div class="body">
<h1>Repositories</h1>

<div class="catalog-list">
% for repo in rows:
<div class="catalog-card">
<p>{{repo["title"]}}</p>
<p><span class="text-id">{{repo["name"]}}</span></p>

</div>
