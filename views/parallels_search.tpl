% extends "base.tpl"

% block title
Parallels
% endblock

% block body

<h1>Parallels Search Results</h1>

% if data is none:
<p>Bad input.</p>
% elif not data:
<p>No results.</p>
% else:
<p>Results
{{(page - 1) * per_page + 1}}-{{(page - 1) * per_page + (data[:per_page] | length)}}
of {{total}}.</p>
% endif

% if data:
<table>
<thead>
<tr>
   <th>Location</th>
   <th>Text</th>
   <th>Similarity</th>
</tr>
</thead>
<tbody>
<tr>
   <td><span class="text-id">-</span></td>
   <td>{{text | safe}}</td>
   <td>1.00</td>
</tr>
% for id, file, number, contents, coeff in data[:per_page]:
<tr>
   <td><a href="/parallels/texts/{{file}}/{{category_plural}}/{{id}}">
      <span class="text-id">{{file.removeprefix("DHARMA_")}}</span> {{number}}
   </a></td>
   <td>{{contents | safe}}</td>
   <td>{{"%.02f" % coeff}}</td>
</tr>
% endfor
</tbody>
</table>

<div class="pagination">
% if page > 1:
   <a href="/parallels/search?text={{orig_text}}&type={{category}}&page={{page - 1}}">← Previous</a>
% else:
   ← Previous
% endif
   |
% if (data | length) > per_page:
   <a href="/parallels/search?text={{orig_text}}&type={{category}}&page={{page + 1}}">Next →</a>
% else:
   Next →
% endif
</div>

% endif

% endblock
