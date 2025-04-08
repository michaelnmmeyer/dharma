% extends "base.tpl"

% block title
% if doc.title:
   {{doc.title.html() | safe}}
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

% if doc.editors:
<p>
{{numberize("Editor", (doc.editors | length))}}:
% for editor_ident, editor_name in doc.editors:
   {{editor_name.html() | safe}}
   (<a href="/people/{{editor_ident.text()}}" class="monospace">{{editor_ident.html() | safe}}</a>){% if loop.index < loop.length %},{% else %}.{% endif %}
% endfor
</p>
% endif

% if doc.summary:
<div class="metadata-paras">
<p>Summary: </p>
{{doc.summary.html() | safe}}
</div>
% endif

% if doc.hand:
<div class="metadata-paras">
<p>Hand description: p>
{{doc.hand.html() | safe}}
</div>
% endif

% if doc.identifier:
<p>Identifier: <span class="text-id">{{doc.identifier.html() | safe}}</span>.</p>
% endif

% if doc.repository:
% if doc.repository.name and doc.repository.identifier:
<p>Repository: {{doc.repository.name.html() | safe}} (<a class="repo-id" href="/repositories/{{doc.repository.identifier.text()}}">{{doc.repository.identifier.html() | safe}}</a>).</p>
% elif doc.repository.name:
<p>Repository: {{doc.repository.name.html() | safe}}.</p>
% elif doc.repository.identifier:
<p>Repository: <a class="repo-id" href="/repositories/{{doc.repository.identifier.text()}}">{{doc.repository.identifier.html() | safe}}</a>.</p>
% endif
% endif

{{doc.body.html() | safe}}

</div><!--id="inscription-display"-->

<!--<div class="hidden" id="inscription-source">
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
</div>-->

% endblock

{#

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

#}

