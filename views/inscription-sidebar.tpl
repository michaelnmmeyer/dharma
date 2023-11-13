<nav><ul>
<li><a href="#metadata">Metadata</a></li>
<li><a href="#edition">Edition</a></li>
% if doc.apparatus:
<li><a href="#apparatus">Apparatus</a></li>
% end
% for i, _ in enumerate(doc.translation, 1):
<li><a href="#translation-{{i}}">Translation</a></li>
% end
% if doc.commentary:
<li><a href="#commentary">Commentary</a></li>
% end
% if doc.bibliography:
<li><a href="#bibliography">Bibliography</a></li>
% end
% if doc.notes:
<li><a href="#notes">Notes</a></li>
% end
</ul></nav>
