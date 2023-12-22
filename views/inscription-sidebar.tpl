<h1>Contents</h1>

<nav><ul>

<li><a href="#metadata">Metadata</a></li>

% if doc.edition:
   % if len(doc.edition) > 1:
<li><a href="#edition">Edition</a><ul>
   % for i, edition in enumerate(doc.edition, 1):
      <li>Edition{{!edition.render_outline()}}</li>
   % end
</ul></li>
   % else:
<li><a href="#edition">Edition</a>{{!doc.edition[0].render_outline()}}</li>
% end

% if doc.apparatus:
<li><a href="#apparatus">Apparatus</a>{{!doc.apparatus.render_outline()}}</li>
% end

% for i, translation in enumerate(doc.translation, 1):
<li><a href="#translation-{{i}}">Translation</a>{{!translation.render_outline()}}</li>
% end

% if doc.commentary:
<li><a href="#commentary">Commentary</a>{{!doc.commentary.render_outline()}}</li>
% end

% if doc.bibliography:
<li><a href="#bibliography">Bibliography</a>{{!doc.bibliography.render_outline()}}</li>
% end

% if doc.notes:
<li><a href="#notes">Notes</a></li>
% end

</ul></nav>
