% rebase("base.tpl", title="Parallels of %s" % loc)
<h1>Parallels of {{loc}}</h1>

% for id, file, verse, text, coeff in verses:
<a href="/parallels/verses/{{id}}">{{file}} {{verse}}</a> {{"%.2f" % coeff}}
<p>
{{!text}}
</p>
% end
