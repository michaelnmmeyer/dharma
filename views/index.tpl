% extends "base.tpl"

% block title
Home
% endblock

% block body

<h1>ERC-DHARMA Database</h1>

<p>For general information about the project and its goals, head over to <a href="https://dharma.hypotheses.org">our blog on Hypotheses.org</a>. The present website allows you to access the
project's database, but it does not record participants' other activities. You migh also want to consult <a href="https://erc-dharma.github.io">our previous website</a>, which is more documented than this one.</p>

<p>The application code was last updated {{code_date}} (see <a
href="https://github.com/michaelnmmeyer/dharma/commit/{{code_hash}}">here</a>).
All dates on this website are in CET.</p>

This website is hosted on a server graciously provided to us by <a href="https://www.huma-num.fr">Huma-Num</a>.

% endblock
