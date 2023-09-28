% rebase("base.tpl", title="Parallels")

<div class="body">

<h1>Parallel
% if category == "padas":
   Pādas
% else:
   {{category.title()}}
% end
of {{file.removeprefix("DHARMA_")}} {{number}}</h1>

</div>

<table>
<thead>
<tr>
   <th>Location</th>
   <th>Text</th>
   <th>Similarity</th>
</tr>
</thead>
<tbody>
<tr>
   <td>{{file.removeprefix("DHARMA_")}} {{number}}</td>
   <td>{{!contents}}</td>
   <td>1.00</td>
</tr>
% for row in data:
<tr>
   <td>
   <a href="/parallels/texts/{{row["file"]}}/{{category}}/{{row["id2"]}}">{{row["file"].removeprefix("DHARMA_")}}</a>
   </td>
   <td>{{row["number"]}}</td>
   <td>{{!row["contents"]}}</td>
   <td>{{"%.02f" % row["coeff"]}}</td>
</tr>
% end
</tbody>
</table>
