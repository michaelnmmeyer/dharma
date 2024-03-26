% extends "base.tpl"

% block title
% if category == "padas":
   Pādas
% else:
   {{category.title()}}
% endif
of <span class="text-id">{{file.removeprefix("DHARMA_")}}</span> {{number}}
% endblock

% block body

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
   <td>{{contents | safe}}</td>
   <td>1.00</td>
</tr>
% for row in data:
<tr>
   <td><a href="/parallels/texts/{{row["file"]}}/{{category}}/{{row["id2"]}}">
      <span class="text-id">{{row["file"].removeprefix("DHARMA_")}}</span>
   {{row["number"]}} </a>
   </td>
   <td>{{row["contents"] | safe}}</td>
   <td>{{"%.02f" % row["coeff"]}}</td>
</tr>
% endfor
</tbody>
</table>

% endblock
