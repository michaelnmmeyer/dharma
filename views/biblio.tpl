% extends "base.tpl"

% block title
Bibliography
% endblock

% block body

<h1>Bibliography</h1>

<p>Entries
{{"%d\N{en dash}%d" % (first_entry, last_entry)}}
of
{{entries_nr}}.
</p>

<div class="pagination">
% if page > 1:
   <a href="/bibliography/page/{{page - 1}}">← Previous</a>
% else:
   ← Previous
% endif
   |
% if page < pages_nr:
   <a href="/bibliography/page/{{page + 1}}">Next →</a>
% else:
   Next →
% endif
</div>

% for entry in entries:
   {{entry | safe}}
% endfor

<div class="pagination">
% if page > 1:
   <a href="/bibliography/page/{{page - 1}}">← Previous</a>
% else:
   ← Previous
% endif
   |
% if page < pages_nr:
   <a href="/bibliography/page/{{page + 1}}">Next →</a>
% else:
   Next →
% endif
</div>

% endblock
