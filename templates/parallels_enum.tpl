% extends "base.tpl"

% block title
Parallels
% endblock

% block body

<h1>Parallel
% if category == "padas":
   Pādas
% else:
   {{category.title()}}
% endif
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
   <td>{{contents | safe}}</td>
   <td>1.00</td>
</tr>
% for row in data:
<tr>
   <td><a href="/parallels/texts/{{row["file"]}}/{{category}}/{{row["id2"]}}">
      <span class="text-id">{{row["file"].removeprefix("DHARMA_")}}</span>
   </a> {{row["number"]}}
   </td>
   <td>{{row["contents"] | safe}}</td>
   <td>{{"%.02f" % row["coeff"]}}</td>
</tr>
% endfor
</tbody>
</table>

% endblock
