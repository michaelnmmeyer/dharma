```{=html}
% extends "base.tpl"

% block title
Editorial Conventions
% endblock

% block body
```

|Description|DHARMA markup|DHARMA display|
|:-----:|:-----:|:-----:|
|Line beginning|`<lb n="1"/>svasti śrī`<br/>   `<lb n="2"/>kōpparakēcari` |(1)<br/>  (2)|
|Word divided across lines|`<lb n="1"/>…dhar`<br/>  `<lb n="2" break="no"/>ma…`|(1)…dhar-<br/>  (2)ma…|
|Tentative reading  (letters ambiguous outside of their context)|`dha<unclear>rma</unclear>`|dha(rma)|
||`dha<unclear cert="low">rma</unclear>`|dha(rma?)|
|Unclear, could be read either a or o|`<choice>`<br/>  `<unclear>a</unclear>`<br/>  `<unclear>o</unclear>`<br/>  `</choice>`|(a/o)|
|Lacuna restored (supplied)|`dha<supplied reason="lost">r</supplied>ma`  `dha<supplied reason="illegible">r</supplied>ma`|dha[rma]<br/>  dha[rma]|
||`dha<supplied reason="lost" cert="low">r</supplied>ma`  `dha<supplied reason="illegible" cert="low">r</supplied>ma`|dha[r?]ma<br/>  dha[r?]ma|
||`dha<supplied reason="omitted">rma</supplied>`|dha⟨rma⟩|
|Restoration based on previous edition (not assessable)|`dha<supplied reason="undefined" evidence="previouseditor"/>rma</supplied>`||
|Restoration based on parallel|`dha<supplied reason="lost" evidence="parallel">abc</supplied>`||
|Unstandard|`<orig>dhamma</orig>`|<span style="color:magenta;">¡dharma!</span> [colour: magenta]|
|Standardisation|`<reg>dharmma</reg>`  <br/>NB: `<reg>` is used only within `<choice>`|<span style="color:blue;">⟨dharmma⟩</span> [colour: blue]|
||`<choice>  <orig>a</orig>  <reg>z</reg>  </choice>`|<span style="color:magenta;">¡a!</span><span style="color:blue;">⟨z⟩</span>|
|Uncorrect|`<sic>dhoma</sic>`|<span style="color:red;">¿dhoma?</span> [colour: red]|
|Correction|`<corr>dharmma</corr>`|<span style="color:green;">⟨dharmma⟩</span> [colour: green]|
||`dha<choice><sic>t</sic><corr>r</corr></choice>ma`|dha<span style="color:red;">¿t?</span><span style="color:green;">⟨r⟩</span>ma|
|Surplus|`dharma<surplus>ma</surplus>`|dharma{ma}|
|Lacuna (<gap>)|`<gap reason="lost" extent="unknown" unit="character"/>`|[...]|
||`<gap reason="lost" unit="character" quantity="1"/>`<br/>  `<gap reason="lost" unit="character" quantity="3"/>`|[1+]  [3+]|
||`<gap reason="lost" unit="character" quantity="1" precision="low"/>`<br/>  `<gap reason="lost" unit="character" quantity="3"precision="low">`|[ca. 3+]|
||`<gap reason="illegible" extent="unknown" unit="character"/>`|[...]|
||`<gap reason="illegible" unit="character" quantity="1"/>`<br/>  `<gap reason="illegible" unit="character" quantity="3"/>`|[1x]<br/>  [3x]|
||`<gap reason="illegible" unit="character" quantity="1" precision="low"/>` <br/> `<gap reason="illegible" unit="character" quantity="3"precision="low"/>`|[ca. 3x]|
||`<gap reason="undefined" extent="unknown" unit="character"/>`|[...]|
||`<gap reason="undefined" unit="character" quantity="1"/>`<br/>  `<gap reason=”undefined" unit="character" quantity="3"/>`|[1\*]<br/>  \[3\*]|
||`<gap reason="undefined" unit="character" quantity="1" precision="low"/>` <br/> `<gap reason="undefined" unit="character" quantity="3"precision="low"/>`|[ca. 1\*]  [ca. 3\*]|
|Line lost|`<gap reason="lost/illegible/undefined" quantity="1" unit="line"/>`|[1 line lost/illegible/ost or illegible]|
|Line(s) lost, extent unknown|`<gap reason="lost/illegible/undefined" extent="unknown" unit="line"/>`|[unknown number of lines lost/illegible/lost or illegible]|
||`<gap reason="lost/illegible/undefined" extent="unknown" unit="line"><certainty match=".." locus="name"/></gap>`|[unknown number of lines possibly lost/illegible/lost or illegible]|
|Line lost, precision low|`<gap reason="lost/illegible/undefined" quantity="3" unit="line" precision="low"/>`|[ca. 3 lines lost/illegible/lost or illegible]|
|Line possibly lost|`<gap reason="lost/illegible/undefined" quantity="1" unit="line"><certainty match=".." locus="name"/></gap>`|[1 line possibly lost/illegible/lost or illegible]|
||`<gap reason="lost/illegible/undefined" quantity="2" unit="line" precision="low"><certainty match=".." locus="name"/></gap>`|[ca. 2 lines possibly lost/illegible/lost or illegible]|
||`<seg met="+++-++"><gap reason="lost" quantity="6" unit="character">`|[– – – ⏑ – –]|
||`<gap reason="illegible" quantity="10" unit="character" precision="low"/><seg met="+++-++"><gap reason="illegible" quantity="6" unit="character"/></seg><supplied reason="lost" evidence="parallel">abc</supplied>`|[ca.10x – – – ⏑ – – abc]|
|Scribal addition|`dha<add>rma</add>`|dha⟨⟨rma⟩⟩|
|Scribal deletion|`dharma<del>ma</del>`|`dharma⟦ma⟧`|
|Consonant|`<seg type="component" subtype="body"/>`||
|Vowel|`<seg type="component" subtype="prescript"/>`<br/>  `<seg type="component" subtype="postcript"/>``||
|Symbol|`<g type="symbol" subtype="golfball"/>`<br/>  `<g type="symbol" subtype="kalam"/>`||
|Grantha|`<hi rend="grantha">svasti śrī</hi>`|**svasti śrī**|
|Italics|`<hi rend="italic">dharma</hi>`|*dharma*|
|Stanza|`<lg n="1" met="āryā">`||
||`<lg n="2" met="+++++-++-+=">`|- - - - - ⏑ - - ⏑ - ⏓|
|verses|`<l n="ab"><lb n="1"/>kāritam idan nr̥patinā`|kāritam idan nr̥patinā|
||`<l n="a"><lb n="1"/>kāritam idan nr̥patinā`|kāritam idan nr̥patinā|
||`<l n="a"><lb n="1"/>kāritam idan nr̥patinā</l>`<br/>  `<l n="b"><lb n="3"/>śrī-śikhari-pallaveśvararam iti</l>`|kāritam idan nr̥patinā<br/> (Ident)śrī-śikhari-pallaveśvararam iti|
||`<foreign>dharma</foreign>`|*dharma*|
||Kantacēṉaṉ `<supplied reason="explanation">Skt. Skandasena</supplied>`|Kantacēṉaṉ (Skt. Skandasena)|
||Temple `<supplied reason="explanation"><foreign>tēvakulam</foreign></supplied>`|Temple (tēvakulam)|
||Fiftieth `<supplied reason="subaudible">year</supplied>` of Nantippōttaracar|Fiftieth [year] of Nantippōttaracar|
||`@enjamb`||
|substitution|`bottun<subst><del rend="corrected">u</del><add place="overstrike">a</add></subst>`|`bottun⟦u⟧⟨⟨a⟩⟩`|

```{=html}
% endblock
```
