% extends "base.tpl"

% block title
Display
% endblock

% block body

<h1>
% if doc.title:
   % for part in doc.title[:-1]:
      {{part | safe}}:
   % endfor
   {{doc.title[-1]}}
% else:
   <i>Untitled</i>.
% endif
</h1>

<p>
{{numberize("Editor", doc.editors | length)}}:
% for ed in doc.editors[:-1]:
   {{ed | safe}},
% endfor
% if doc.editors:
   {{doc.editors[-1] | safe}}.
% else:
   <i>Anonymous editor</i>.
% endif
</p>
<p>
Identifier: <span class="text-id">{{text}}</span>.
</p>
% if doc.summary:
<p>Summary: {{doc.summary.render_logical() | safe}}</p>
% endif

% if doc.langs:
<p>Languages:
   % for lang in doc.langs[:-1]:
      {{lang}},
   % endfor
      {{doc.langs[-1]}}.
</p>
% endif

% if doc.repository:
<p>Repository: <span class="repo-id">{{doc.repository}}</span>.</p>
% endif

% if doc.commit_date:
<p>
Version: {{doc.commit_date}}
(<a href="{{github_url}}"><span class="commit-hash">{{doc.commit_hash[:7]}}</span></a>), last modified
{{doc.last_modified}} (<span class="commit-hash">{{doc.last_modified_commit[:7]}}</span>).
</p>
% endif

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
{{doc.edition.render_logical() | safe}}
</div>

<div class="phys" id="phys" style="display:none">
{{doc.edition.render_physical() | safe}}
</div>

<div class="full" id="full" style="display:none">
{{doc.edition.render_full() | safe}}
</div>

</div> <!-- <div class="ed"> -->
% endif

<div class="xml" id="xml" style="display:none">
<pre>
{{doc.xml | safe}}
</pre>
</div>

% if doc.apparatus:
<div class="apparatus">
<h2 id="apparatus">Apparatus</h2>
{{doc.apparatus.render_logical() | safe}}
</div>
% endif

% for i, trans in enumerate(doc.translation, 1):
<div class="trans">
<h2 id="translation-{{i}}">{{trans.title | safe}}</h2>
{{trans.render_logical() | safe}}
</div>
% endfor

% if doc.commentary:
<div class="trans">
<h2 id="commentary">Commentary</h2>
{{doc.commentary.render_logical() | safe}}
</div>
% endif

% if doc.bibliography:
<div class="biblio">
<h2 id="bibliography">Bibliography</h2>
{{doc.bibliography.render_logical() | safe}}
</div>
% endif

% if doc.notes:
<div class="notes">
<h2 id="notes">Notes</h2>
% for i, note in enumerate(doc.notes, 1):
<div class="note" id="note-{{i}}">
<a class="note-ref" href="#note-ref-{{i}}">↑{{i}}</a>
{{note.render_logical | safe}}
</div>
% endfor
</div>
% endif

% endblock
