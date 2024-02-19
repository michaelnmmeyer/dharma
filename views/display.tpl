% rebase("base.tpl", title="Display")

<h1>Display</h1>

<ul>
% for text in texts:
<li><a href="/display/{{text}}">{{text.removeprefix("DHARMA_")}}</a></li>
% end
</ul>

</div>
