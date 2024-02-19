% rebase("base.tpl", title="Languages")

<h1>Languages</h1>

<p>The following table displays languages that currently appear in the DHARMA database.</p>

<table>
<thead>
<tr>
   <th>Name</th>
   <th>Codes</th>
   <th>ISO Standard</th>
</tr>
</thead>
<tbody>
% for row in rows:
<tr>
   <td>{{row["name"]}}</td>
   <td>{{", ".join(json.loads(row["codes"]))}}</td>
   <td>{{row["iso"]}}</td>
</tr>
% end
</tbody>
</table>

<p>For the ISO 639-3 standard (languages), see <a
href="https://iso639-3.sil.org">here</a>.</p>

<p>For the ISO 639-5 standard (families of languages), see <a
href="https://www.loc.gov/standards/iso639-5/index.html">here</a>.</p>
