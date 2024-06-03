% extends "base.tpl"

% block title
Bibliography Errors
% endblock

% block body

<p>The following enumerates duplicate short titles in our Zotero bibliography.</p>

<ul>
% for (short_title,) in entries:
   <li>{{short_title}}</li>
% endfor
</ul>

% endblock
