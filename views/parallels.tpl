% rebase("base.tpl", title="Parallels")

<div class="body">

<h1>Parallels</h1>

<p>Parallels database last updated {{last_updated}}.</p>

<p>This interface allows you to look for parallel verse passages—verses,
hemistiches or pādas—in the DHARMA texts collection. Parallels are found with
an approximate matching technique which is described below. You can either
input a passage to look for in the form below, or browse the collection with
the table at the bottom of this page.</p>

<p>When searching for a verse, add a daṇḍa at the end of the first hemistich
(and none before that). You should always input a complete passage—verse,
hemistich or pāda, depending on the unit you choose. This interface is not
meant to be used for searching arbitrary substrings.</p>

<form action="/parallels/search" method="get">
<label for="text-input">Text:</label>
<input name="text" id="text-input"></input>
<label for="select-type">Unit:</label>
<select name="type" id="select-type">
   <option value="verse">Verse</option>
   <option value="hemistich">Hemistich</option>
   <option value="pada">Pāda</option>
</select>
<input type="submit" value="Search">
</form>

<p>The table at the bottom of this page displays, for each text that has at
least one parallel, the number of verses, hemistiches and pādas it contains
that have parallels in the DHARMA collection.</p>

<p>Verse passages that are encoded in a weird way are omitted from parallels.
Please use one <code>&lt;l&gt;</code> element per pāda, and number pādas with
lowercase ASCII letters in alphabet order, without gaps in the numbering.</p>

<p>Currently, we ignore the fact that parallels might cross verse boundaries.
To be more explicit: when looking for parallels of a given verse, we compare it
to verses 1, 2, 3, etc. of each text, but we do not try to compare it to 1cd-2ab,
2cd-3ab, etc. This might be changed in the future.
</p>

<p>The similarity measure we are currently using for comparing passages is the
<a href="https://en.wikipedia.org/wiki/Jaccard_index">Jaccard index</a>
<i>J</i>, computed over sets of character <a
href="https://en.wikipedia.org/wiki/N-gram">trigrams</a>. <i>J</i> = 1 when
passages share the exact same set of trigrams, <i>J</i> = 0 when they do not
share a single one. We (arbitrarily) assume that pairs of passages for which
<i>J</i> < 0.3 are not parallels, and do not display them. See <a
href="https://github.com/michaelnmmeyer/dharma/blob/master/ngrams.py">here</a>
for details.</p>

<div class="table-container">
<table>
<thead>
<tr>
   <th>File</th>
   <th>Verses</th>
   <th>Hemistiches</th>
   <th>Pādas</th>
</tr>
</thead>
<tbody>
% for row in data:
<tr>
   <td>{{row["file"].removeprefix("DHARMA_")}}</td>
% for category in ("verses", "hemistiches", "padas"):
   <td>
   % if row[category] > 0:
   <a href="/parallels/texts/{{row["file"]}}/{{category}}">{{row[category]}}</a>
   % else:
   {{row[category]}}
   % end
   </td>
% end
</tr>
% end
</tbody>
</table>
</div>

</div>
