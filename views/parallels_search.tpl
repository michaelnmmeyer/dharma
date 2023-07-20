% rebase("base.tpl", title="Parallels")

<div class="body">
<h1>Parallels Search Results</h1>

% if data is None:

<p>Bad input.</p>

% else:

<table>
<thead>
<tr>
   <th>File</th>
   <th>Location</th>
   <th>Text</th>
   <th>Similarity</th>
</tr>
</thead>
<tbody>
<tr>
   <td>-</td>
   <td>-</td>
   <td>{{!text}}</td>
   <td>1.00</td>
</tr>
% for id, file, number, contents, coeff in data:
<tr>
   <td>
   <a href="/parallels/texts/{{file}}/{{category}}/{{id}}">{{file.removeprefix("DHARMA_")}}</a>
   </td>
   <td>{{number}}</td>
   <td>{{!contents}}</td>
   <td>{{"%.02f" % coeff}}</td>
</tr>
% end
</tbody>

%end

</div>
