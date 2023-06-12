<table>
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
