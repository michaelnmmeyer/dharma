% rebase("base.tpl", title="Texts")

<div class="body">
<h1>Texts</h1>
<div>
<p>Last updated {{last_updated}}.</p>

<form action="/texts" method="get">
<label for="select-owner">Edited by:</label>
<select name="owner" id="select-owner">
% if owner:
   <option value="">Anybody</option>
% else:
   <option value="" selected>Anybody</option>
% end
% for author_id, author_name in authors:
   % if author_id == owner:
      <option value="{{author_id}}" selected>{{author_name}}</option>
   % else:
      <option value="{{author_id}}">{{author_name}}</option>
   % end
% end
</select>
<input type="submit" value="Reload">
</form>
</div>
</div>

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
   <td><a
   href="texts/{{text["repo"]}}/{{text["commit_hash"]}}/{{text["name"]}}">{{text["name"].removeprefix("DHARMA_")}}</a></td>
% if text["valid"]:
   <td>✓</td>
% else:
   <td><a href="texts/{{text["repo"]}}/{{text["commit_hash"]}}/{{text["name"]}}">🐛</a></td>
% end
   <td>
% if text["html_path"]:
   <a href="https://erc-dharma.github.io/{{text['repo']}}/{{text['html_path']}}">🔗</a>
% else:
   ∅
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
