% extends "base.tpl"

% block title
% if doc.titles:
   {{doc.titles[0].html() | safe}}
% else:
   <i>Untitled</i>
% endif
% endblock

% block body

{{doc.body.html() | safe}}

% endblock body
