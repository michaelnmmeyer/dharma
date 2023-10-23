% rebase("base.tpl", title="Test")

<div class="body">
<h1>Catalog</h1>

<p>⏓-⏑--⏑⏓</p>
<p>⏓ - ⏑ - - ⏑ ⏓</p>

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

</div>
