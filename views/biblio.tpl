% rebase("base.tpl", title="Bibliography")

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
% end
   |
% if page < pages_nr:
   <a href="/bibliography/page/{{page + 1}}">Next →</a>
% else:
   Next →
% end
</div>

% for entry in entries:
   {{!entry}}
% end

<div class="pagination">
% if page > 1:
   <a href="/bibliography/page/{{page - 1}}">← Previous</a>
% else:
   ← Previous
% end
   |
% if page < pages_nr:
   <a href="/bibliography/page/{{page + 1}}">Next →</a>
% else:
   Next →
% end
</div>
