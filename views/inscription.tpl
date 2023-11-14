% rebase("base.tpl", title="Display", includes='''
   <link rel="stylesheet" href="/inscription.css">
	<script src="/pack.js"></script>
	<script src="/inscription.js"></script>
''', sidebar=sidebar)

<div class="body">

<h1 id="metadata">
% if doc.title:
   % for part in doc.title:
      {{!part}}.
   % end
% else:
   <i>Untitled</i>.
% end
</h1>

<p>
{{numberize("Editor", len(doc.editors))}}:
% for ed in doc.editors[:-1]:
   {{!ed}},
% end
% if doc.editors:
   {{!doc.editors[-1]}}.
% else:
   <i>Anonymous editor</i>.
% end
</p>
<p>
Identifier: <span class="dh-text-id">{{text}}</span>
</p>
% if doc.summary:
<p>Summary: {{!doc.summary.render_logical()}}</p>
% end
% if doc.langs:
<p>Languages:
   % for lang in doc.langs[:-1]:
      {{lang}},
   % end
      {{doc.langs[-1]}}.
</p>
% end

<div class="dh-ed">

<h2 id="edition">Edition</h2>

<ul class="dh-ed-tabs">
   <li id="log-btn" class="dh-active"><a href="#dh-ed">Logical</a></li>
   <li id="phys-btn"><a href="#dh-ed">Physical</a></li>
   <li id="xml-btn"><a href="#dh-ed">XML</a></li>
</ul>

<div class="dh-log" id="dh-log">
{{!doc.edition.render_logical()}}
</div>

<div class="dh-phys" id="dh-phys" style="display:none">
{{!doc.edition.render_physical()}}
</div>

</div> <!-- <div class="dh-ed"> -->

</div> <!-- <div class="body"> -->

<div class="dh-xml" id="dh-xml" style="display:none">
<pre>
{{!doc.xml}}
</pre>
</div>

<div class="body">

% if doc.apparatus:
<div class="dh-apparatus">
<h2 id="apparatus">Apparatus</h2>
{{!doc.apparatus.render_logical()}}
</div>
% end

% for i, trans in enumerate(doc.translation, 1):
<div class="dh-trans">
<h2 id="translation-{{i}}">Translation</h2>
{{!trans.render_logical()}}
</div>
% end

% if doc.commentary:
<div class="dh-trans">
<h2 id="commentary">Commentary</h2>
{{!doc.commentary.render_logical()}}
</div>
% end

% if doc.bibliography:
<div class="dh-biblio">
<h2 id="bibliography">Bibliography</h2>
{{!doc.bibliography.render_logical()}}
</div>
% end

% if doc.notes:
<div class="dh-notes">
<h2 id="notes">Notes</h2>
% for i, note in enumerate(doc.notes, 1):
<div class="dh-note" id="note-{{i}}">
<a class="dh-note-ref" href="#note-ref-{{i}}">↑{{i}}</a>
{{!note.render_logical()}}
</div>
% end
</div>
% end

</div> <!-- <div class="body"> -->

<div id="dh-tip-box">
   <div id="dh-tip-contents"></div>
   <div id="dh-tip-arrow" data-popper-arrow></div>
</div>
