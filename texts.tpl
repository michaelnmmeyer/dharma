% rebase("base.tpl", title="Texts")
<h1>Texts</h1>
<table>
<thead>
<tr>
   <th>Identifier</th>
   <th>Status</th>
</tr>
<tbody>
% for name, err in texts:
<tr>
   <td><a href="texts/{{name}}">{{name}}</a></td>
% if err:
   <td>🐛</td>
% else:
   <td>✓</td>
% end
</tr>
% end
</tbody>
</table>
