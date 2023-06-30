% rebase("base.tpl", title=text["name"])
<h1>{{text["name"]}}</h1>
<p>Committed {{text['readable_commit_date']}} in
<a href="https://github.com/erc-dharma/{{text['repo']}}/commit/{{text['commit_hash']}}">{{text["commit_hash"][:7]}}...</a>
</p>
<p>Validated {{text['readable_when_validated']}}.</p>
<table>
<thead>
<tr>
   <th>Location</th>
   <th>Message</th>
</tr>
</thead>
<tbody>
% for line, col, msg in text["errors"]:
<tr>
   <td><a href="{{github_url}}#L{{line}}">{{line}}:{{col}}</a></td>
   <td>{{msg}}</td>
</tr>
% end
</tbody>
</table>
