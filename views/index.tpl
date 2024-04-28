% extends "base.tpl"

% block title
DHARMA Database
% endblock

% block body

You might want to consult <a href="https://erc-dharma.github.io">our previous
website</a>, which is more documented than this one.

<p>The application code was last updated {{code_date | format_date}} (see <a
href="https://github.com/michaelnmmeyer/dharma/commit/{{code_hash}}">here</a>).
</p>

<p>Our legal notice is <a href="/legal-notice">here</a>.</p>

% endblock
