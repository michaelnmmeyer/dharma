% rebase("base.tpl", title="Parallel Verses")
<h1>Verse Parallels</h1>

% for id, file, verse, text, count in verses:
<a href="/parallels/verses/{{id}}">{{file}} {{verse}}</a> ({{count}} parallels)
<p>
{{!text}}
</p>
% end
