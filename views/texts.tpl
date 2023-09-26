% rebase("base.tpl", title="Texts")

<div class="body">
<h1>Texts</h1>

<p>Texts database last updated {{last_updated}}.</p>

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

<div class="table-container">
<table>
<thead>
<tr>
   <th>Identifier</th>
   <th>Status</th>
   <th>Repository</th>
   <th>Commit date</th>
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
   <a href="https://github.com/erc-dharma/{{text['repo']}}">{{text["repo"]}}</a>
   </td>
   <td>{{text["readable_commit_date"]}}</td>
</tr>
% end
</tbody>
</table>
</div>
