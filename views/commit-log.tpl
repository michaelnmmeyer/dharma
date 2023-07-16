% rebase("base.tpl", title="Commit Log")

<div class="body">
<h1>Commit Log</h1>
</div>

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
   <td><a
   href="https://github.com/erc-dharma/{{commit['repo']}}">{{commit["repo"]}}</a>
   </td>
   <td><a href="{{commit['url']}}">{{commit["hash"]}}</a></td>
</tr>
% end
</tbody>
</table>
