% rebase("base.tpl", title="Texts")

<div class="body">
<h1>Texts</h1>

<p>Texts database last updated {{last_updated}}.</p>

<p>This table now only shows problematic files. You can use the
<a href="/catalog">catalog interface</a> for searching texts.</p>

<p>The "severity" parameter is interpreted as follows:</p>
<ul>
   <li>Warning. The file might present some problems but is OK overall.
   <li>Error. The file does not adhere to the guidelines and might thus not be
   processed correctly.</li>
   <li>Fatal. The file is not valid XML and cannot be processed at all. It is
   not possible to display it, to search it, etc.</li>
</ul>

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
<label for="select-severity">Severity:</label>
<select name="severity" id="select-severity">
% for value in ("warning", "error", "fatal"):
% if value == severity:
   <option value="{{value}}" selected>{{value.title()}}</option>
% else:
   <option value="{{value}}">{{value.title()}}</option>
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
   <th>Repository</th>
   <th>Commit date</th>
</tr>
<tbody>
% for text in texts:
<tr>
   <td><a href="texts/{{text["name"]}}">{{text["name"].removeprefix("DHARMA_")}}</a></td>
   <td>
   <a href="https://github.com/erc-dharma/{{text['repo']}}">{{text["repo"]}}</a>
   </td>
   <td>{{text["readable_commit_date"]}}</td>
</tr>
% end
</tbody>
</table>
</div>
