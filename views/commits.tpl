% rebase("base.tpl", title="Commits")

<div class="body">
<h1>Commits</h1>

<p>This displays commits across all DHARMA repositories, including private
ones, which you might not be able to access.</p>

</div>

<table>
<thead>
<tr>
   <th>Push date</th>
   <th>Author</th>
   <th>Repository</th>
</tr>
</thead>
<tbody>
% for commit in commits:
<tr data-href="{{commit['url']}}">
   <td>{{commit["date"]}}</td>
   <td>{{commit["author"]}}</td>
   <td><span class="repo-id">{{commit["repo"]}}</span></td>
</tr>
% end
</tbody>
</table>
