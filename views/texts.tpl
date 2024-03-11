% rebase("base.tpl", title="Texts")

<h1>Texts</h1>

<p>Texts database last updated {{last_updated}}.</p>

<p>This table only shows problematic files. You can use the
<a href="/catalog">catalog interface</a> for consulting all DHARMA texts.</p>

<p>In the form below, the "Edited by" field refers to Git's commit history, not
to the editors mentioned in the XML file's <code>&lt;teiHeader&gt;</code>. Thus, if
you select your name, you will see files that you modified at some point, even
if you are not credited as an editor. Conversely, the files where you are
credited as an editor but that you did not modify yourself will not be shown.</p>

<p>The "Severity" parameter indicates how serious the problem is. There are
three severity levels:</p>
<ul>
   <li>"Warning". The file might present some Unicode problems.
   <li>"Error". The file does not adhere to the guidelines and might thus not be
   processed correctly.</li>
   <li>"Fatal". The file is not well-formed XML and cannot be processed at all.</li>
</ul>

<p>As a rule, files with a "Fatal" severity level should be amended as soon as
possible, because it is impossible to do anything with them. To check whether
a file is well-formed XML in Oxygen, click on the downwards arrow next to the "Validate"
button in the toolbar, and click on "Check Well-Formedness".</p>

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
   <td><a href="texts/{{text["name"]}}">
      <span class="text-id">{{text["name"].removeprefix("DHARMA_")}}</span>
   </a></td>
   <td><a href="https://github.com/erc-dharma/{{text['repo']}}">
      <span class="repo-id">{{text["repo"]}}</span>
   </a></td>
   <td>{{text["readable_commit_date"]}}</td>
</tr>
% end
</tbody>
</table>
