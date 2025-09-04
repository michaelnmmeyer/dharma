% extends "base.tpl"

% block title
Languages
% endblock

% block body

<p>The following only displays languages that currently appear in the DHARMA database.</p>

<div class="catalog-list">

% for row in rows:
<div id="lang-{{row['lang']}}" class="catalog-card">

<p>
	<b>{{row["name"]}}</b> [<span class="monospace">{{row["lang"]}}</span>]
% if row["prod"] is not none:
	(<a href="{{url_for('show_catalog', q='lang:' + row['lang'])}}">{{row["prod"]}} {{numberize("text", row["prod"])}}</a>)
% endif
</p>

% if row["repos"]:
<p>
Repositories:
% for repo, repo_prod in from_json(row["repos"]):
   <span class="repo-id">{{repo}}</span>
   (<a href="{{url_for('show_catalog', q='lang:%s repo:%s' % (row["lang"], repo))}}">{{repo_prod}}</a>){{loop.index == loop.length and "." or ","}}
% endfor
</p>
% endif

% if row["editors"]:
<p>
Editors:
% for editor_id, editor, editor_prod in from_json(row["editors"]):
   {{editor}}
   (<a href="{{url_for('show_catalog', q='lang:%s editor_id:%s' % (row["lang"], editor_id))}}">{{editor_prod}}</a>){{loop.index == loop.length and "." or ","}}
% endfor
</p>
% endif

<p>Standard: {{row["standard"]}}.</p>

</div>
% endfor

</div> <!-- class="catalog-list" -->

<p>For the canonical list of languages of the DHARMA project, see <a href="https://github.com/erc-dharma/project-documentation/blob/master/DHARMA_languages.tsv">here</a>.</p>

<p>For the ISO 639-3 standard (languages), see <a
href="https://iso639-3.sil.org">here</a>.</p>

<p>For the ISO 639-5 standard (families of languages), see <a
href="https://www.loc.gov/standards/iso639-5/index.html">here</a>.</p>

% endblock
