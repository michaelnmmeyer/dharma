% rebase("base.tpl", title=text_id)
<h1>{{text_id}}</h1>
<table>
<thead>
<tr>
   <th>Location</th>
   <th>Message</th>
</tr>
</thead>
<tbody>
% for line, col, msg in errors:
<tr>
   <td><a
   href="https://github.com/michaelnmmeyer/dharma/blob/master/texts/{{text_id}}.xml#L{{line}}">{{line}}:{{col}}</a></td>
   <td>{{msg}}</td>
</tr>
% end
</tbody>
</table>
