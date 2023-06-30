% rebase("base.tpl", title="Home")
<h1>DHARMA Development Server</h1>

<p>All dates are in CEST (UTC+2).</p>

<ul>
   <li><a href="/commit-log">Commit log</a></li>
   <li><a href="/texts">Texts</a></li>
   <li><a href="/parallels/verses">Parallel Verses</a></li>
</ul>

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
