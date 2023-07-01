% rebase("base.tpl", title="Texts")
<h1>Texts</h1>
<p>Last updated {{last_updated}}.</p>
<table>
<thead>
<tr>
   <th>Identifier</th>
   <th>Status</th>
   <th>Repository</th>
   <th>Commit date</th>
   <th>Commit hash</th>
</tr>
<tbody>
% for text in texts:
<tr>
   <td><a href="texts/{{text["repo"]}}/{{text["commit_hash"]}}/{{text["name"]}}">{{text["name"]}}</a></td>
% if text["valid"]:
   <td>✓</td>
% else:
   <td>🐛</td>
% end
   <td>
   <a href="https://github.com/erc-dharma/{{text['repo']}}">{{text["repo"]}}</a>
   {{text['html_path']}}
   </td>
   <td>{{text["readable_commit_date"]}}</td>
   <td>
   <a
   href="https://github.com/erc-dharma/{{text['repo']}}/commit/{{text['commit_hash']}}">{{text["commit_hash"][:7]}}...</a>
   </td>
</tr>
% end
</tbody>
</table>
