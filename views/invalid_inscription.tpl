% extends "base.tpl"

% block title
{{text}}
% endblock

% block body

<div id="inscription-display">
<p>This inscription's XML source is malformed.</p>
</div>

<div id="inscription-source">
<fieldset>
<legend>Display Options</legend>
	<label>Word Wrap
		<input class="display-option" name="xml-wrap" type="checkbox" checked>
	</label>
	<label>Line Numbers
		<input class="display-option" name="xml-line-nos" type="checkbox" checked>
	</label>
</fieldset>
<div id="xml" class="xml xml-wrap xml-line-nos">
{{highlighted_xml | safe}}
</div>
</div>

% endblock
