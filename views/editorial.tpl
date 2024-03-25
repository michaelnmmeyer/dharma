% extends "base.tpl"

% block title
Documentation
% endblock

% block body
<table>
<colgroup>
<col style="width: 33%" />
<col style="width: 33%" />
<col style="width: 33%" />
</colgroup>
<thead>
<tr class="header">
<th style="text-align: center;">Description</th>
<th style="text-align: center;">DHARMA markup</th>
<th style="text-align: center;">DHARMA display</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td style="text-align: center;">Line beginning</td>
<td
style="text-align: center;"><code>&lt;lb n="1"/&gt;svasti śrī</code><br/>
<code>&lt;lb n="2"/&gt;kōpparakēcari</code></td>
<td style="text-align: center;">(1)<br/> (2)</td>
</tr>
<tr class="even">
<td style="text-align: center;">Word divided across lines</td>
<td style="text-align: center;"><code>&lt;lb n="1"/&gt;…dhar</code><br/>
<code>&lt;lb n="2" break="no"/&gt;ma…</code></td>
<td style="text-align: center;">(1)…dhar-<br/> (2)ma…</td>
</tr>
<tr class="odd">
<td style="text-align: center;">Tentative reading (letters ambiguous
outside of their context)</td>
<td
style="text-align: center;"><code>dha&lt;unclear&gt;rma&lt;/unclear&gt;</code></td>
<td style="text-align: center;">dha(rma)</td>
</tr>
<tr class="even">
<td style="text-align: center;"></td>
<td
style="text-align: center;"><code>dha&lt;unclear cert="low"&gt;rma&lt;/unclear&gt;</code></td>
<td style="text-align: center;">dha(rma?)</td>
</tr>
<tr class="odd">
<td style="text-align: center;">Unclear, could be read either a or
o</td>
<td style="text-align: center;"><code>&lt;choice&gt;</code><br/>
<code>&lt;unclear&gt;a&lt;/unclear&gt;</code><br/>
<code>&lt;unclear&gt;o&lt;/unclear&gt;</code><br/>
<code>&lt;/choice&gt;</code></td>
<td style="text-align: center;">(a/o)</td>
</tr>
<tr class="even">
<td style="text-align: center;">Lacuna restored (supplied)</td>
<td
style="text-align: center;"><code>dha&lt;supplied reason="lost"&gt;r&lt;/supplied&gt;ma</code>
<code>dha&lt;supplied reason="illegible"&gt;r&lt;/supplied&gt;ma</code></td>
<td style="text-align: center;">dha[rma]<br/> dha[rma]</td>
</tr>
<tr class="odd">
<td style="text-align: center;"></td>
<td
style="text-align: center;"><code>dha&lt;supplied reason="lost" cert="low"&gt;r&lt;/supplied&gt;ma</code>
<code>dha&lt;supplied reason="illegible" cert="low"&gt;r&lt;/supplied&gt;ma</code></td>
<td style="text-align: center;">dha[r?]ma<br/> dha[r?]ma</td>
</tr>
<tr class="even">
<td style="text-align: center;"></td>
<td
style="text-align: center;"><code>dha&lt;supplied reason="omitted"&gt;rma&lt;/supplied&gt;</code></td>
<td style="text-align: center;">dha⟨rma⟩</td>
</tr>
<tr class="odd">
<td style="text-align: center;">Restoration based on previous edition
(not assessable)</td>
<td
style="text-align: center;"><code>dha&lt;supplied reason="undefined" evidence="previouseditor"/&gt;rma&lt;/supplied&gt;</code></td>
<td style="text-align: center;"></td>
</tr>
<tr class="even">
<td style="text-align: center;">Restoration based on parallel</td>
<td
style="text-align: center;"><code>dha&lt;supplied reason="lost" evidence="parallel"&gt;abc&lt;/supplied&gt;</code></td>
<td style="text-align: center;"></td>
</tr>
<tr class="odd">
<td style="text-align: center;">Unstandard</td>
<td
style="text-align: center;"><code>&lt;orig&gt;dhamma&lt;/orig&gt;</code></td>
<td style="text-align: center;"><span
style="color:magenta;">¡dharma!</span> [colour: magenta]</td>
</tr>
<tr class="even">
<td style="text-align: center;">Standardisation</td>
<td
style="text-align: center;"><code>&lt;reg&gt;dharmma&lt;/reg&gt;</code>
<br/>NB: <code>&lt;reg&gt;</code> is used only within
<code>&lt;choice&gt;</code></td>
<td style="text-align: center;"><span
style="color:blue;">⟨dharmma⟩</span> [colour: blue]</td>
</tr>
<tr class="odd">
<td style="text-align: center;"></td>
<td
style="text-align: center;"><code>&lt;choice&gt;  &lt;orig&gt;a&lt;/orig&gt;  &lt;reg&gt;z&lt;/reg&gt;  &lt;/choice&gt;</code></td>
<td style="text-align: center;"><span
style="color:magenta;">¡a!</span><span
style="color:blue;">⟨z⟩</span></td>
</tr>
<tr class="even">
<td style="text-align: center;">Uncorrect</td>
<td
style="text-align: center;"><code>&lt;sic&gt;dhoma&lt;/sic&gt;</code></td>
<td style="text-align: center;"><span style="color:red;">¿dhoma?</span>
[colour: red]</td>
</tr>
<tr class="odd">
<td style="text-align: center;">Correction</td>
<td
style="text-align: center;"><code>&lt;corr&gt;dharmma&lt;/corr&gt;</code></td>
<td style="text-align: center;"><span
style="color:green;">⟨dharmma⟩</span> [colour: green]</td>
</tr>
<tr class="even">
<td style="text-align: center;"></td>
<td
style="text-align: center;"><code>dha&lt;choice&gt;&lt;sic&gt;t&lt;/sic&gt;&lt;corr&gt;r&lt;/corr&gt;&lt;/choice&gt;ma</code></td>
<td style="text-align: center;">dha<span
style="color:red;">¿t?</span><span
style="color:green;">⟨r⟩</span>ma</td>
</tr>
<tr class="odd">
<td style="text-align: center;">Surplus</td>
<td
style="text-align: center;"><code>dharma&lt;surplus&gt;ma&lt;/surplus&gt;</code></td>
<td style="text-align: center;">dharma{ma}</td>
</tr>
<tr class="even">
<td style="text-align: center;">Lacuna (<gap>)</td>
<td
style="text-align: center;"><code>&lt;gap reason="lost" extent="unknown" unit="character"/&gt;</code></td>
<td style="text-align: center;">[…]</td>
</tr>
<tr class="odd">
<td style="text-align: center;"></td>
<td
style="text-align: center;"><code>&lt;gap reason="lost" unit="character" quantity="1"/&gt;</code><br/>
<code>&lt;gap reason="lost" unit="character" quantity="3"/&gt;</code></td>
<td style="text-align: center;">[1+] [3+]</td>
</tr>
<tr class="even">
<td style="text-align: center;"></td>
<td
style="text-align: center;"><code>&lt;gap reason="lost" unit="character" quantity="1" precision="low"/&gt;</code><br/>
<code>&lt;gap reason="lost" unit="character" quantity="3"precision="low"&gt;</code></td>
<td style="text-align: center;">[ca. 3+]</td>
</tr>
<tr class="odd">
<td style="text-align: center;"></td>
<td
style="text-align: center;"><code>&lt;gap reason="illegible" extent="unknown" unit="character"/&gt;</code></td>
<td style="text-align: center;">[…]</td>
</tr>
<tr class="even">
<td style="text-align: center;"></td>
<td
style="text-align: center;"><code>&lt;gap reason="illegible" unit="character" quantity="1"/&gt;</code><br/>
<code>&lt;gap reason="illegible" unit="character" quantity="3"/&gt;</code></td>
<td style="text-align: center;">[1x]<br/> [3x]</td>
</tr>
<tr class="odd">
<td style="text-align: center;"></td>
<td
style="text-align: center;"><code>&lt;gap reason="illegible" unit="character" quantity="1" precision="low"/&gt;</code>
<br/>
<code>&lt;gap reason="illegible" unit="character" quantity="3"precision="low"/&gt;</code></td>
<td style="text-align: center;">[ca. 3x]</td>
</tr>
<tr class="even">
<td style="text-align: center;"></td>
<td
style="text-align: center;"><code>&lt;gap reason="undefined" extent="unknown" unit="character"/&gt;</code></td>
<td style="text-align: center;">[…]</td>
</tr>
<tr class="odd">
<td style="text-align: center;"></td>
<td
style="text-align: center;"><code>&lt;gap reason="undefined" unit="character" quantity="1"/&gt;</code><br/>
<code>&lt;gap reason=”undefined" unit="character" quantity="3"/&gt;</code></td>
<td style="text-align: center;">[1*]<br/> [3*]</td>
</tr>
<tr class="even">
<td style="text-align: center;"></td>
<td
style="text-align: center;"><code>&lt;gap reason="undefined" unit="character" quantity="1" precision="low"/&gt;</code>
<br/>
<code>&lt;gap reason="undefined" unit="character" quantity="3"precision="low"/&gt;</code></td>
<td style="text-align: center;">[ca. 1*] [ca. 3*]</td>
</tr>
<tr class="odd">
<td style="text-align: center;">Line lost</td>
<td
style="text-align: center;"><code>&lt;gap reason="lost/illegible/undefined" quantity="1" unit="line"/&gt;</code></td>
<td style="text-align: center;">[1 line lost/illegible/ost or
illegible]</td>
</tr>
<tr class="even">
<td style="text-align: center;">Line(s) lost, extent unknown</td>
<td
style="text-align: center;"><code>&lt;gap reason="lost/illegible/undefined" extent="unknown" unit="line"/&gt;</code></td>
<td style="text-align: center;">[unknown number of lines
lost/illegible/lost or illegible]</td>
</tr>
<tr class="odd">
<td style="text-align: center;"></td>
<td
style="text-align: center;"><code>&lt;gap reason="lost/illegible/undefined" extent="unknown" unit="line"&gt;&lt;certainty match=".." locus="name"/&gt;&lt;/gap&gt;</code></td>
<td style="text-align: center;">[unknown number of lines possibly
lost/illegible/lost or illegible]</td>
</tr>
<tr class="even">
<td style="text-align: center;">Line lost, precision low</td>
<td
style="text-align: center;"><code>&lt;gap reason="lost/illegible/undefined" quantity="3" unit="line" precision="low"/&gt;</code></td>
<td style="text-align: center;">[ca. 3 lines lost/illegible/lost or
illegible]</td>
</tr>
<tr class="odd">
<td style="text-align: center;">Line possibly lost</td>
<td
style="text-align: center;"><code>&lt;gap reason="lost/illegible/undefined" quantity="1" unit="line"&gt;&lt;certainty match=".." locus="name"/&gt;&lt;/gap&gt;</code></td>
<td style="text-align: center;">[1 line possibly lost/illegible/lost or
illegible]</td>
</tr>
<tr class="even">
<td style="text-align: center;"></td>
<td
style="text-align: center;"><code>&lt;gap reason="lost/illegible/undefined" quantity="2" unit="line" precision="low"&gt;&lt;certainty match=".." locus="name"/&gt;&lt;/gap&gt;</code></td>
<td style="text-align: center;">[ca. 2 lines possibly
lost/illegible/lost or illegible]</td>
</tr>
<tr class="odd">
<td style="text-align: center;"></td>
<td
style="text-align: center;"><code>&lt;seg met="+++-++"&gt;&lt;gap reason="lost" quantity="6" unit="character"&gt;</code></td>
<td style="text-align: center;">[– – – ⏑ – –]</td>
</tr>
<tr class="even">
<td style="text-align: center;"></td>
<td
style="text-align: center;"><code>&lt;gap reason="illegible" quantity="10" unit="character" precision="low"/&gt;&lt;seg met="+++-++"&gt;&lt;gap reason="illegible" quantity="6" unit="character"/&gt;&lt;/seg&gt;&lt;supplied reason="lost" evidence="parallel"&gt;abc&lt;/supplied&gt;</code></td>
<td style="text-align: center;">[ca.10x – – – ⏑ – – abc]</td>
</tr>
<tr class="odd">
<td style="text-align: center;">Scribal addition</td>
<td
style="text-align: center;"><code>dha&lt;add&gt;rma&lt;/add&gt;</code></td>
<td style="text-align: center;">dha⟨⟨rma⟩⟩</td>
</tr>
<tr class="even">
<td style="text-align: center;">Scribal deletion</td>
<td
style="text-align: center;"><code>dharma&lt;del&gt;ma&lt;/del&gt;</code></td>
<td style="text-align: center;"><code>dharma⟦ma⟧</code></td>
</tr>
<tr class="odd">
<td style="text-align: center;">Consonant</td>
<td
style="text-align: center;"><code>&lt;seg type="component" subtype="body"/&gt;</code></td>
<td style="text-align: center;"></td>
</tr>
<tr class="even">
<td style="text-align: center;">Vowel</td>
<td
style="text-align: center;"><code>&lt;seg type="component" subtype="prescript"/&gt;</code><br/>
<code>&lt;seg type="component" subtype="postcript"/&gt;``|| |Symbol|</code><g type="symbol" subtype="golfball"/><code>&lt;br/&gt;</code><g type="symbol" subtype="kalam"/><code>|| |Grantha|</code><hi rend="grantha">svasti
śrī</hi><code>|**svasti śrī**| |Italics|</code><hi rend="italic">dharma</hi><code>|*dharma*| |Stanza|</code><lg n="1" met="āryā"><code>|| ||</code><lg n="2" met="+++++-++-+="><code>|- - - - - ⏑ - - ⏑ - ⏓| |verses|</code><l n="ab"><lb n="1"/>kāritam
idan
nr̥patinā<code>|kāritam idan nr̥patinā| ||</code><l n="a"><lb n="1"/>kāritam
idan
nr̥patinā<code>|kāritam idan nr̥patinā| ||</code><l n="a"><lb n="1"/>kāritam
idan
nr̥patinā</l><code>&lt;br/&gt;</code><l n="b"><lb n="3"/>śrī-śikhari-pallaveśvararam
iti</l><code>|kāritam idan nr̥patinā&lt;br/&gt; (Ident)śrī-śikhari-pallaveśvararam iti| ||</code><foreign>dharma</foreign><code>|*dharma*| ||Kantacēṉaṉ</code><supplied reason="explanation">Skt.
Skandasena</supplied><code>|Kantacēṉaṉ (Skt. Skandasena)| ||Temple</code><supplied reason="explanation"><foreign>tēvakulam</foreign></supplied><code>|Temple (tēvakulam)| ||Fiftieth</code><supplied reason="subaudible">year</supplied><code>of Nantippōttaracar|Fiftieth [year] of Nantippōttaracar| ||</code><span
class="citation"
data-cites="enjamb">@enjamb</span><code>|| |substitution|</code>bottun<subst><del rend="corrected">u</del><add place="overstrike">a</add></subst><code>|</code>bottun⟦u⟧⟨⟨a⟩⟩`</td>
<td style="text-align: center;"></td>
</tr>
</tbody>
</table>
% endblock
