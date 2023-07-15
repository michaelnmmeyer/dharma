% rebase("base.tpl", title=text["name"])
<h1>{{text["name"]}}</h1>
<p>Committed {{text['readable_commit_date']}} in
<a
href="https://github.com/erc-dharma/{{text['repo']}}/commit/{{text['commit_hash']}}">{{text["commit_hash"]}}</a>.
</p>
<p>Validated {{text['readable_when_validated']}}.</p>

% if text["errors"]["unicode"]:
<h2>Unicode Issues</h2>
<p>
This is a list of
<a
href="https://unicode.org/reports/tr29/#Grapheme_Cluster_Boundaries">grapheme
clusters</a> that are likely invalid. Each row highlights the problematic
text segment and enumerates the names of the <a
href="https://unicode.org/glossary/#code_point">code points</a> that compose it.
If you find grapheme clusters that are actually valid, please send me their
list of code points at <a
href="mailto:michaelnm.meyer@gmail.com">michaelnm.meyer@gmail.com</a>,
so that I update the code.
</p>
<table>
<thead>
<tr>
   <th>Line</th>
   <th>Message</th>
</tr>
</thead>
<tbody>
% for rec in text["errors"]["unicode"]:
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

% if text["errors"]["schema"]:
<h2>Schema Validation Issues</h2>
<table>
<thead>
<tr>
   <th>Line</th>
   <th>Message</th>
</tr>
</thead>
<tbody>
% for line, col, msg in text["errors"]["schema"]:
<tr>
   <td><a href="{{github_url}}#L{{line}}">{{line}}</a></td>
   <td>{{msg}}</td>
</tr>
% end
</tbody>
</table>
% end
