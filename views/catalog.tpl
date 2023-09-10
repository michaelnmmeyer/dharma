% rebase("base.tpl", title="Catalog")

<div class="body">
<h1>Catalog</h1>

<table>
<thead></thead>
<tbody>
% for row in rows:
<tr><td>
   <p>
   % if not row["html_link"].endswith("/"):
      <a href="{{row["html_link"]}}">
   % end
   % if row["title"]:
      % for chunk in row["title"]:
         {{chunk.rstrip(".")}}.
      % end
   % else:
      <i>Untitled</i>.
   % end
   % if not row["html_link"].endswith("/"):
      </a>
   % end
   </p>
   <p>
   % for ed in row["editors"][:-1]:
      {{ed}},
   % end
   % if row["editors"]:
      {{row["editors"][-1]}}.
   % else:
      <i>Anonymous editor</i>.
   % end
   </p>
   <p>{{row["name"].removeprefix("DHARMA_")}} ({{row["repo"]}}).</p>
</td></tr>
% end
</tbody>
</table>
