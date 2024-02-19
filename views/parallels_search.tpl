% rebase("base.tpl", title="Parallels")

<h1>Parallels Search Results</h1>

% if data is None:
<p>Bad input.</p>
% elif not data:
<p>No results.</p>
% else:
<p>Results
{{(page - 1) * per_page + 1}}-{{(page - 1) * per_page + len(data[:per_page])}}
of {{total}}.</p>
% end

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
   <td>{{!text}}</td>
   <td>1.00</td>
</tr>
% for id, file, number, contents, coeff in data[:per_page]:
<tr>
   <td><a href="/parallels/texts/{{file}}/{{category_plural}}/{{id}}">
      <span class="text-id">{{file.removeprefix("DHARMA_")}}</span> {{number}}
   </a></td>
   <td>{{!contents}}</td>
   <td>{{"%.02f" % coeff}}</td>
</tr>
% end
</tbody>
</table>

<div class="pagination">
% if page > 1:
   <a href="/parallels/search?text={{orig_text}}&type={{category}}&page={{page - 1}}">← Previous</a>
% else:
   ← Previous
% end
   |
% if len(data)	> per_page:
   <a href="/parallels/search?text={{orig_text}}&type={{category}}&page={{page + 1}}">Next →</a>
% else:
   Next →
% end
</div>

% end # if data:
