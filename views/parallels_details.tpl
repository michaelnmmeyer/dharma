% rebase("base.tpl", title="Parallels")

<h1>
% if category == "padas":
   Pādas
% else:
   {{category.title()}}
% end
of <span class="text-id">{{file.removeprefix("DHARMA_")}}</span> that Have Parallels</h1>

<table>
<thead>
<tr>
   <th>Location</th>
   <th>Text</th>
   <th>Number of Parallels</th>
</tr>
</thead>
<tbody>
% for row in data:
<tr>
   <td><a href="/parallels/texts/{{file}}/{{category}}/{{row["id"]}}">
      <span class="text-id">{{row["number"]}}</span>
   </a></td>
   <td>{{!row["contents"]}}</td>
   <td>{{row["parallels"]}}</td>
% end
</tr>
</tbody>
</table>
