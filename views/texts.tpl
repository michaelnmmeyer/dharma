% extends "base.tpl"

% block title
Texts
% endblock

% block body

<p>Texts database last updated {{last_updated | format_date}}.</p>

<p>This interface allows you to look for texts in the DHARMA collection. The
search form below can be used for filtering results. Matching is
case-insensitive, does not take diacritics into account, and looks for
substrings instead of terms. For instance, the query <a
href="{{url_for("show_catalog", q="edit")}}">edit</a> matches "edition" or "meditation". To look for
a phrase, surround it with double quotes, as in <a
href="/texts?q=&quot;old%20javanese&quot;">&quot;old javanese&quot;</a>.
Searching for strings that contain less than three characters is not
possible.</p>

<p>Per default, all metadata fields are searched (except "lang", see below).
Metadata fields are (for now): "title", "editor", "editor_id", "author", "summary",
"lang", "repo", "ident". You can restrict search to a specific field by using a
field prefix, as in <a href="{{url_for('show_catalog', q='editor:manu')}}">editor:manu</a> or <a
href="/texts?q=title:&quot;critical%20edition&quot;">title:"critical
edition"</a>. Several clauses can be added successively, separated with
whitespace. In this case, for a document to be considered a match, all query
clauses must match. Try for instance <a
href="{{url_for("show_catalog", q='editor:manu title:stone')}}">editor:manu title:stone</a>.</p>

<p>Note the use of quotation marks: the query <a href="/texts?q=editor:&quot;emmanuel%20francis&quot;">editor:"emmanuel francis"</a> matches all documents edited by Emmanuel Francis, but the query <a href="/texts?q=editor:emmanuel%20francis">editor:emmanuel francis</a> matches all documents edited by someone called Emmanuel <em>and that also include the name Francis in any metadata field</em>.</p>

<p>The "lang" field is special. If you look for a string that contains two or
three letters only, as in <a href="{{url_for("show_catalog", q="lang:en")}}">lang:en</a> or <a
href="{{url_for("show_catalog", q="lang:san")}}">lang:san</a>, it is assumed to refer to an ISO 639
language code, and an exact comparison is performed. If you look for a string
longer than that, it is assumed to refer to a language name and the
above-mentioned substring matching technique will be used instead. You can consult a
table of languages <a href="/langs">here</a>.</p>

<form action="{{url_for("show_catalog")}}" method="get">
<ul>
   <li>
   <label for="text-input">Find:</label>
   % if q:
   <input name="q" id="text-input" value="{{q | escape}}" autofocus/>
   % else:
   <input name="q" id="text-input" autofocus/>
   % endif
   </li>
   <li>
<label for="sort-select">Sort by:</label>
<select name="s" id="sort-select">
% for k, v in (("title", "Title"), ("repo", "Repository"), ("ident", "Identifier")):
   % if k == s:
      <option value="{{k}}" selected>{{v}}</option>
   % else:
      <option value="{{k}}">{{v}}</option>
   % endif
% endfor
</select>
   </li>
   <li>
<input type="submit" value="Search">
   </li>
</ul>
</form>

<p>Documents
{{"%d\N{en dash}%d" % (first_entry, last_entry)}}
of
{{entries_nr}}
% if q:
matching.
% else:
total.
% endif
</p>

<div class="catalog-list">
% for row in rows:
<div class="catalog-card">
   <div class="catalog-card-heading">
   % if row["name"].startswith("DHARMA_INS"):
      <a href="{{url_for("display_text", text=row["name"])}}">
   % elif row["html_path"]:
      <a href="{{format_url('https://erc-dharma.github.io/%s/%s', row['repo'], row['html_path'])}}">
   % endif
   % if row["title"]:
      {{row["title"] | safe}}
   % else:
      <i>Untitled</i>
   % endif
   % if row["name"].startswith("DHARMA_INS") or row["html_path"]:
      </a>
   % endif
   </div>
   <p>
   % for ed in row["editors"][:-1]:
      {{ed | safe}},
   % endfor
   % if row["editors"]:
      {{row["editors"][-1] | safe}}.
   % else:
      <i>Anonymous editor</i>.
   % endif
   </p>
   % if row["summary"]:
   <p>Summary: {{row["summary"] | safe}}</p>
   % endif
   % if row["langs"]:
   % set langs = from_json(row["langs"])
   <p>{{numberize("Language", langs | length)}}:
      % for lang in langs:
      % if loop.index < loop.length:
         {{lang}},
      % else:
         {{lang}}.
      % endif
      % endfor
   </p>
   % endif
   <p>
      Repository: {{row["repo_title"]}} (<span class="repo-id">{{row["repo"]}}</span>).
   </p>
   <p><span class="text-id">{{row["name"]}}</span>.</p>
</div>
% endfor
</div>

<div class="pagination">
% if page > 1:
   <a href="{{url_for('show_catalog', q=q, p=page - 1, s=s)}}">← Previous</a>
% else:
   ← Previous
% endif
   |
% if page < pages_nr:
   <a href="{{url_for('show_catalog', q=q, p=page + 1, s=s)}}">Next →</a>
% else:
   Next →
% endif
</div>

% endblock
