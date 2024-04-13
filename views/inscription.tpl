% extends "base.tpl"

% block title
% if doc.title:
   {{doc.title | safe}}
% else:
   <i>Untitled</i>
% endif
% endblock

% block sidebar
% if row:
<div class="toc-heading">External Links</div>
<nav>
<ul>
<li><a href="{{row['github_download_url']}}"><i class="fa-solid fa-code"></i> XML File</a></li>
% if row['static_website_url']:
<li>🦕 <a href="{{row['static_website_url']}}">Old Display</a></li>
% endif
</ul>
</nav>
% endif
% endblock


% block body

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

% if doc.edition_main_langs:
<p>Languages:
   % for lang in doc.edition_main_langs:
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
(<a href="{{github_commit_url}}"><span class="commit-hash">{{doc.commit_hash[:7]}}</span></a>), last modified
{{doc.last_modified | format_date}} (<a href="{{github_last_modified_commit_url}}"><span class="commit-hash">{{doc.last_modified_commit[:7]}}</span></a>).
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
   <li id="xml-btn"><a href="#ed">XML</a></li>
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

<div class="xml hidden" id="xml" data-display="xml">
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

% for trans in doc.translation:
<div class="trans">
<h2 id="translation-{{loop.index}}">{{trans.title | safe}}</h2>
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

% endblock
