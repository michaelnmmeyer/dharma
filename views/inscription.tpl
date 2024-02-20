% rebase("base.tpl", title="Display", includes='''
   <link rel="stylesheet" href="/inscription.css">
   <script src="/inscription.js"></script>
''')

<h1>
% if doc.title:
   % for part in doc.title:
      {{!part}}.
   % end
% else:
   <i>Untitled</i>.
% end
</h1>

<p>
{{numberize("Editor", len(doc.editors))}}:
% for ed in doc.editors[:-1]:
   {{!ed}},
% end
% if doc.editors:
   {{!doc.editors[-1]}}.
% else:
   <i>Anonymous editor</i>.
% end
</p>
<p>
Identifier: <span class="text-id">{{text}}</span>.
</p>
% if doc.summary:
<p>Summary: {{!doc.summary.render_logical()}}</p>
% end

% if doc.langs:
<p>Languages:
   % for lang in doc.langs[:-1]:
      {{lang}},
   % end
      {{doc.langs[-1]}}.
</p>
% end

<p>Repository: <span class="repo-id">{{doc.repository}}</span>.</p>

<p>
Version: {{doc.commit_date}}
(<a href="{{github_url}}"><span class="commit-hash">{{doc.commit_hash[:7]}}</span></a>), last modified
{{doc.last_modified}} (<span class="commit-hash">{{doc.last_modified_commit[:7]}}</span>).
</p>

% if doc.edition:
<div class="ed">

<h2 id="edition">Edition</h2>

<ul class="ed-tabs">
   <li id="log-btn" class="active"><a href="#ed">Logical</a></li>
   <li id="phys-btn"><a href="#ed">Physical</a></li>
   <li id="full-btn"><a href="#ed">Full</a></li>
   <li id="xml-btn"><a href="#ed">XML</a></li>
</ul>

<div class="log" id="log">
{{!doc.edition.render_logical()}}
</div>

<div class="phys" id="phys" style="display:none">
{{!doc.edition.render_physical()}}
</div>

<div class="full" id="full" style="display:none">
{{!doc.edition.render_full()}}
</div>

</div> <!-- <div class="ed"> -->
% end # if doc.edition:

<div class="xml" id="xml" style="display:none">
<pre>
{{!doc.xml}}
</pre>
</div>

% if doc.apparatus:
<div class="apparatus">
<h2 id="apparatus">Apparatus</h2>
{{!doc.apparatus.render_logical()}}
</div>
% end

% for i, trans in enumerate(doc.translation, 1):
<div class="trans">
<h2 id="translation-{{i}}">Translation</h2>
{{!trans.render_logical()}}
</div>
% end

% if doc.commentary:
<div class="trans">
<h2 id="commentary">Commentary</h2>
{{!doc.commentary.render_logical()}}
</div>
% end

% if doc.bibliography:
<div class="biblio">
<h2 id="bibliography">Bibliography</h2>
{{!doc.bibliography.render_logical()}}
</div>
% end

% if doc.notes:
<div class="notes">
<h2 id="notes">Notes</h2>
% for i, note in enumerate(doc.notes, 1):
<div class="note" id="note-{{i}}">
<a class="note-ref" href="#note-ref-{{i}}">↑{{i}}</a>
{{!note.render_logical()}}
</div>
% end
</div>
% end
