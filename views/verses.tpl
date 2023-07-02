% rebase("base.tpl", title="Parallel Verses")

<div class="body">
<h1>Parallel Verses</h1>

<p>
The similarity measure we are currently using for comparing verses is the <a
href="https://en.wikipedia.org/wiki/Jaccard_index">Jaccard index</a> <i>J</i>,
computed over sets of character trigrams (<a
href="https://en.wikipedia.org/wiki/N-gram"><i>n</i>-grams</a> of size 3). <i>J</i> = 1
when verses share the exact same set of trigrams, <i>J</i> = 0 when they do not
share a single one. We (arbitrarily) assume that pairs of verses for which
<i>J</i> <= 0.3 are not parallels, and do not display them. We also omit verses
which do not have parallels.
</p>

<ul>
% for id, file, verse, text, count in verses:
<li>
<a href="/parallels/verses/{{id}}">{{file}} {{verse}}</a> ({{count}}
% if count == 1:
parallel)
%else:
parallels)
%end
<div class="verse">
% for line in text:
<p class="verse">{{line}}</p>
% end
</div>
</li>
% end
</ul>
</div>
