% extends "base.tpl"

% block title
People
% endblock

% block body

<div class="catalog-list">

% for row in rows:
<div class="catalog-card" id="person-{{row['dh_id']}}">

<p>
<b>{{row['inverted_name']}}</b>
(<span class="member-id">{{row['dh_id']}}</span>)
</p>

% if row["affiliation"]
<p>{{row["affiliation"]}}</p>
% endif

% if row["idhal"] or row["idref"] or row["orcid"] or row["viaf"] or row["wikidata"]:
<p>
% if row['idhal']:
<a href="https://cv.archives-ouvertes.fr/{{row['idhal']}}">IdHAL</a>
% endif
% if row['idref']:
<a href="https://www.idref.fr/{{row['idref']}}">IdRef</a>
% endif
% if row['orcid']:
<a href="https://orcid.org/{{row['orcid']}}">ORCID</a>
% endif
% if row['viaf']:
<a href="https://viaf.org/viaf/{{row['viaf']}}">VIAF</a>
% endif
% if row['wikidata']:
<a href="https://www.wikidata.org/wiki/{{row['wikidata']}}">Wikidata</a>
% endif
</p>
% endif

</div>
% endfor

</div> <!-- class="catalog-list" -->

% endblock

