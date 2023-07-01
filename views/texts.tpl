% rebase("base.tpl", title="Texts")
<h1>Texts</h1>
<p>Last updated {{last_updated}}.</p>
<table>
<thead>
<tr>
   <th>Identifier</th>
   <th>Status</th>
   <th>HTML</th>
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
% if text["html_path"]:
   <a href="https://erc-dharma.github.io/{{text['repo']}}/{{text['html_path']}}">🔗</a>
% end
   </td>
   <td>
   <a href="https://github.com/erc-dharma/{{text['repo']}}">{{text["repo"]}}</a>
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
