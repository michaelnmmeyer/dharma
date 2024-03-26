% extends "base.tpl"

% block title
% if category == "padas":
   Pādas
% else:
   {{category.title()}}
% endif
   of <span class="text-id">{{file.removeprefix("DHARMA_")}}</span>
   that Have Parallels
% endblock

% block body

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
   <td>{{row["contents"] | safe}}</td>
   <td>{{row["parallels"]}}</td>
% endfor
</tr>
</tbody>
</table>

% endblock
