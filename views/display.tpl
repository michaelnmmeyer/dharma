% extends "base.tpl"

% block title
Display
% endblock

% block body

<h1>Display</h1>

<ul>
% for text in texts:
<li><a href="{{url_for("display_text", text=text)}}">{{text.removeprefix("DHARMA_")}}</a></li>
% endfor
</ul>

</div>

% endblock
