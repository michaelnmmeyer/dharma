% extends "base.tpl"

% block title
% if doc.title:
   {{doc.title | safe}}
% else:
   <i>Untitled</i>
% endif
% endblock

% block sidebar
<div class="toc-heading">Display</div>
<label>Source view
   <input id="toggle-xml-display" type="checkbox">
</label>
% if row:
<div class="toc-heading">External Links</div>
<nav>
<ul>
<li><a href="{{row['github_download_url']}}"><i class="fa-solid fa-code"></i> XML File</a></li>
% if row['static_website_url']:
<li><a href="{{row['static_website_url']}}">🦕 Old Display</a></li>
% endif
</ul>
</nav>
% endif
% endblock

% block body
<div id="inscription-display">

<p>
{{numberize("Editor", (doc.editors | length))}}:
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

% if doc.edition_langs:
<p>{{numberize("Language", len(doc.edition_langs))}}:
   % for lang in doc.edition_langs:
      % if loop.index < loop.length:
         {{lang}},
      % else:
         {{lang}}.
      % endif
   % endfor
</p>
% endif

% if doc.repository:
<p>Repository: {{repo_title}} (<span class="repo-id">{{doc.repository}}</span>).</p>
% endif

% if doc.commit_date:
<p>
Version: {{doc.commit_date | format_date}}
(<a href="{{github_commit_url}}">{{doc.commit_hash | format_commit_hash}}</a>), last modified
{{doc.last_modified | format_date}} (<a href="{{github_last_modified_commit_url}}">{{doc.last_modified_commit | format_commit_hash}}</a>).
</p>
% endif

% if not doc.valid:
<h2>🐛 Invalid inscription</h2>
% endif

% if doc.edition:
<div class="edition">

<h2 id="edition">Edition</h2>

<ul class="ed-tabs">
   <li id="logical-btn" class="active"><a href="#ed">Logical</a></li>
   <li id="physical-btn"><a href="#ed">Physical</a></li>
   <li id="full-btn"><a href="#ed">Full</a></li>
</ul>

<div class="logical" id="logical" data-display="logical">
{{doc.edition.render_logical() | safe}}
</div>

<div class="physical hidden" id="physical" data-display="physical">
{{doc.edition.render_physical() | safe}}
</div>

<div class="full hidden" id="full" data-display="full">
{{doc.edition.render_full() | safe}}
</div>

</div> <!-- <div class="ed"> -->
% endif

% if doc.apparatus:
<div class="apparatus">
   <h2 id="apparatus" class="collapsible">
      Apparatus <i class="fa-solid fa-angles-down"></i>
   </h2>
   <div class="collapsible-content">
   {{doc.apparatus.render_logical() | safe}}
   </div>
</div>
% endif

% for trans in doc.translation:
<div class="translation">
<h2 id="translation-{{loop.index}}">{{trans.title | safe}}</h2>
{{trans.render_logical() | safe}}
</div>
% endfor

% if doc.commentary:
<div class="commentary">
<h2 id="commentary">Commentary</h2>
{{doc.commentary.render_logical() | safe}}
</div>
% endif

% if doc.bibliography:
<div class="bibliography">
<h2 id="bibliography">Bibliography</h2>
{{doc.bibliography.render_logical() | safe}}
</div>
% endif

% if doc.notes:
<div class="notes">
<h2 id="notes">Notes</h2>
<ol>
% for note in doc.notes:
<li class="note" id="note-{{loop.index}}">
<a class="note-ref" href="#note-ref-{{loop.index}}">{{loop.index}}.</a>
{{note.render_logical() | safe}}
</li>
% endfor
</ol>
</div>
% endif

</div><!-- id="inscription-display" -->
<div class="hidden" id="inscription-source">
<fieldset>
<legend>Display Options</legend>
	<label>Word Wrap
		<input class="display-option" name="xml-wrap" type="checkbox" checked>
	</label>
	<label>Line Numbers
		<input class="display-option" name="xml-line-nos" type="checkbox" checked>
	</label>
	<label>Comments
		<input class="display-option" name="xml-hide-comments" type="checkbox" checked>
	</label>
	<label>Processing Instructions
		<input class="display-option" name="xml-hide-instructions" type="checkbox" checked>
	</label>
</fieldset>
<div id="xml" class="xml xml-wrap xml-line-nos">
{{doc.xml | safe}}
</div>
</div>
% endblock
