<h1>Contents</h1>

<nav><ul>
<li><a href="#metadata">Metadata</a></li>
<li><a href="#edition">Edition</a>{{!doc.edition.render_outline()}}</li>
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
