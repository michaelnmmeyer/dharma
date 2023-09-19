% rebase("base.tpl", title="Catalog")

<div class="body">
<h1>Catalog</h1>

<p>Catalog database last updated {{last_updated}}.</p>

<p>This interface allows you to look for texts in the DHARMA collection. The
search form below can be used for filtering results. Matching is
case-insensitive, does not take diacritics into account, and looks for
substrings instead of terms. For instance, the query <a
href="/catalog?q=edit">edit</a> matches "edition" or "meditation". To look for
a phrase, surround it with double quotes, as in <a
href="/catalog?q=&quot;old%20javanese&quot;">&quot;old javanese&quot;</a>.
Searching for strings that contain less than three characters is not
possible.</p>

<p>Per default, all metadata fields are searched. Metadata fields are (for
now): title, editor, summary, repo, ident. You can restric search to a specific
field by using a field prefix, as in <a
href="/catalog?q=editor:manu">editor:manu</a> or <a
href="/catalog?q=title:&quot;critical%20edition&quot">title:"critical
edition"</a>. Several clauses can be added successively, separated with
whitespace. In this case, for a document to be considered a match, all query
clauses must match. Try for instance <a
href="/catalog?q=editor:manu%20title:stone">editor:manu title:stone</a>.</p>

<form action="/catalog" method="get">
<input name="q" id="text-input"
% if q != "*":
   value="{{q}}"
% else:
   autofocus
% end
></input>
<input type="submit" value="Search">
</form>

<p>Have {{len(rows)}} documents.</p>

<table>
<thead></thead>
<tbody>
% for row in rows:
<tr><td>
   <p>
   % if not row["html_link"].endswith("/"):
      <a href="{{row["html_link"]}}">
   % end
   % if row["author"]:
      {{row["author"]}}.
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
   % if row["summary"]:
   <p>Summary: {{row["summary"]}}</p>
   % end
   <p>{{row["name"].removeprefix("DHARMA_")}} ({{row["repo"]}}).</p>
</td></tr>
% end
</tbody>
</table>
