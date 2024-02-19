% rebase("base.tpl", title="Parallels")

<h1>Parallel
% if category == "padas":
   Pādas
% else:
   {{category.title()}}
% end
of <span class="text-id">{{file.removeprefix("DHARMA_")}}</span> {{number}}</h1>

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
   <td><span class="text-id">{{file.removeprefix("DHARMA_")}}</span> {{number}}</td>
   <td>{{!contents}}</td>
   <td>1.00</td>
</tr>
% for row in data:
<tr>
   <td><a href="/parallels/texts/{{row["file"]}}/{{category}}/{{row["id2"]}}">
      <span class="text-id">{{row["file"].removeprefix("DHARMA_")}}</span>
   </a></td>
   <td>{{row["number"]}}</td>
   <td>{{!row["contents"]}}</td>
   <td>{{"%.02f" % row["coeff"]}}</td>
</tr>
% end
</tbody>
</table>
