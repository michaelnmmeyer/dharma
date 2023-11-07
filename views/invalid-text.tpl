% rebase("base.tpl", title=text["name"].removeprefix("DHARMA_"))

<div class="body">
<h1>{{text["name"].removeprefix("DHARMA_")}}</h1>
<p>Committed {{text["readable_commit_date"]}} in
<a
href="https://github.com/erc-dharma/{{text["repo"]}}/commit/{{text["commit_hash"]}}">{{text["commit_hash"]}}</a>.
</p>
<p>Validated {{text["readable_when_validated"]}}.</p>
</div>

% if result.unicode:
<div class="body">
<h2>Unexpected Unicode Characters</h2>
<p>
This is a list of
<a
href="https://unicode.org/reports/tr29/#Grapheme_Cluster_Boundaries">grapheme
clusters</a> that are likely invalid. Each row highlights a problematic
text segment and enumerates the names of the <a
href="https://unicode.org/glossary/#code_point">code points</a> that compose it.
If you find grapheme clusters that are actually valid, please send me their
list of code points, so that I update the code.
</p>
</div>

<table>
<thead>
<tr>
   <th>Line</th>
   <th>Message</th>
</tr>
</thead>
<tbody>
% for rec in result.unicode:
<tr>
   <td><a href="{{github_url}}#L{{rec["line_no"]}}">{{rec["line_no"]}}</a></td>
   <td>
      <pre style="white-space:pre-line;">{{!rec["highlighted_line"]}}</pre>
      <ol>
      % for name in rec["grapheme"]:
         <li>{{name}}</li>
      % end
      </ol>
   </td>
% end
% end
</tbody>
</table>

% if result.messages:
<div class="body">
<h2>Schema Validation Issues</h2>
</div>

<table>
<thead>
<tr>
   <th>Line</th>
   <th>Message</th>
</tr>
</thead>
<tbody>
% for msg in result.messages:
<tr>
   <td><a href="{{github_url}}#L{{msg.line}}">{{msg.line}}</a></td>
   <td>{{msg.text}}</td>
</tr>
% end
</tbody>
</table>
% end
