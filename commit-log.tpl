% rebase("base.tpl", title="Commit log")
<h1>Commit log</h1>
<table>
<thead>
<tr>
   <th>Push date</th>
   <th>Author</th>
   <th>Repository</th>
   <th>Hash</th>
</tr>
</thead>
<tbody>
% for commit in commits:
<tr>
   <td>{{commit["date"]}}</td>
   <td>{{commit["author"]}}</td>
   <td>{{commit["repo"]}}</td>
   <td><a href="{{commit['url']}}">{{commit["hash"]}}</a></td>
</tr>
% end
</tbody>
</table>
