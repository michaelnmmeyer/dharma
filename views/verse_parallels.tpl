% rebase("base.tpl", title="Parallels of %s" % loc)

<div class="body">

<h1>Parallels of {{loc}}</h1>

<ul>
% for id, file, verse, text, coeff in verses:
   <li>
   <a href="/parallels/verses/{{id}}">{{file}} {{verse}}</a> {{"%.2f" % coeff}}
   <div class="verse">
   % for line in text:
      <p class="verse">{{line}}</p>
   % end
   </div>
   </li>
% end
</ul>

</div>
