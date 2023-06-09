
<table>
<tbody>

% for commit in commits:

<tr>
   <td>{{commit["date"]}}</td>
   <td>{{commit["author"]}}</td>
   <td><a href="{{commit['url']}}">{{commit["hash"]}}</a></td>
   <td>{{commit["repo"]}}</td>

% end

</tbody>
</table>
