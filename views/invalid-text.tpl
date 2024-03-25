% extends "base.tpl"

% block title
{{text["name"].removeprefix("DHARMA_")}}
% endblock

% block body

<h1><span class="text-id">{{text["name"].removeprefix("DHARMA_")}}</span></h1>
<p>Committed {{text["commit_date"] | format_date}} in
<a
href="https://github.com/erc-dharma/{{text["repo"]}}/commit/{{text["commit_hash"]}}"><span class="commit-hash">{{text["commit_hash"]}}</span></a>.
</p>

% if result.unicode:
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
      <pre style="white-space:pre-line;">{{rec["highlighted_line"] | safe}}</pre>
      <ol>
      % for name in rec["grapheme"]:
         <li>{{name}}</li>
      % endfor
      </ol>
   </td>
% endfor
</tbody>
</table>
% endif

% if result.messages:
<h2>Schema Validation Issues</h2>

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
% endfor
</tbody>
</table>
% endif

% endblock
