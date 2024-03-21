% extends "base.tpl"

% block title
Catalog
% endblock

% block body

<h1>Catalog</h1>

<p>Texts database last updated {{last_updated}}.</p>

<p>This interface allows you to look for texts in the DHARMA collection. The
search form below can be used for filtering results. Matching is
case-insensitive, does not take diacritics into account, and looks for
substrings instead of terms. For instance, the query <a
href="/catalog?q=edit">edit</a> matches "edition" or "meditation". To look for
a phrase, surround it with double quotes, as in <a
href="/catalog?q=&quot;old%20javanese&quot;">&quot;old javanese&quot;</a>.
Searching for strings that contain less than three characters is not
possible.</p>

<p>Per default, all metadata fields are searched (except "lang", see below).
Metadata fields are (for now): "title", "editor", "summary", "lang", "repo",
"ident". You can restrict search to a specific field by using a field prefix,
as in <a href="/catalog?q=editor:manu">editor:manu</a> or <a
href="/catalog?q=title:&quot;critical%20edition&quot">title:"critical
edition"</a>. Several clauses can be added successively, separated with
whitespace. In this case, for a document to be considered a match, all query
clauses must match. Try for instance <a
href="/catalog?q=editor:manu%20title:stone">editor:manu title:stone</a>.</p>

<p>The "lang" field is special. If you look for a string that contains two or
three letters only, as in <a href="/catalog?q=lang:en">lang:en</a> or <a
href="/catalog?q=lang:san">lang:san</a>, it is assumed to refer to an ISO 639
language code, and an exact comparison is performed. If you look for a string
longer than that, it is assumed to refer to a language name and the
above-mentioned substring matching technique will be used instead. You can consult a
table of languages <a href="/langs">here</a>.</p>

<form action="/catalog" method="get">
<ul>
   <li>
<label for="text-input">Find:</label>
<input name="q" id="text-input"
% if q != "*":
   value="{{q}}"
% else:
   autofocus
% endif
></input>
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

<p>Have {{rows | length}} documents.</p>

<div class="catalog-list">
% for row in rows:
<div class="catalog-card">
   <p>
   % if row["name"].startswith("DHARMA_INS"):
      <a href="/display/{{row["name"]}}">
   % elif row["html_path"]:
      <a href="{{format_url('https://erc-dharma.github.io/%s/%s', row['repo'], row['html_path'])}}">
   % endif
   % if row["title"]:
      % for chunk in row["title"]:
         {{chunk.rstrip(".") | safe}}.
      % endfor
   % else:
      <i>Untitled</i>.
   % endif
   % if row["name"].startswith("DHARMA_INS") or row["html_path"]:
      </a>
   % endif
   % if row["html_path"] and row["name"].startswith("DHARMA_INS"):
      <a href="{{format_url('https://erc-dharma.github.io/%s/%s', row['repo'], row['html_path'])}}">
      [🦕 Old display]
      </a>
   % endif
   </p>
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
   <p>Languages:
      % for lang in from_json(row["langs"])[:-1]:
         {{lang}},
      % endfor
         {{from_json(row["langs"])[-1]}}.
   </p>
   % endif
   <p>
      <span class="text-id">{{row["name"]}}</span>
      (<span class="repo-id">{{row["repo"]}}</span>).
   </p>
</div>
% endfor
</div>

% endblock
