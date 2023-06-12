<table>
<tbody>
% for line, col, msg in errors:
<tr>
   <td>{{line}}</td>
   <td>{{col}}</td>
   <td>{{msg}}</td>
</tr>
% end
</tbody>
</table>

