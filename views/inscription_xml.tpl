% extends "base.tpl"

% block title
{{text}}
% endblock

% block body
<fieldset>
<legend>Display Options</legend>
<div>
	<label>Line Numbers
		<input class="display-option" name="xml-line-no" type="checkbox">
	</label>
</div>
<div>
	<label>Comments
		<input class="display-option" name="comment" type="checkbox" checked>
	</label>
</div>
<div>
	<label>Processing Instructions
		<input class="display-option" name="instruction" type="checkbox" checked>
	</label>
</div>
</fieldset>

<div class="xml" id="xml">
{{doc.xml | safe}}
</div>

% endblock
