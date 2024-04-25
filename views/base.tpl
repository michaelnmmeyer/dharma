<!doctype html>
<html lang="en">
<head>
   <meta charset="utf-8">
   <meta name="viewport" content="width=device-width, initial-scale=1">
   <title>{{self.title() | striptags}} - DHARMA</title>
   <!-- We have ?v={{code_hash}} in links below to force assets to be
   reloaded by web browsers. -->
   <link rel="stylesheet" href="/fonts.css?v={{code_hash}}">
   <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
   <link rel="stylesheet" href="/base.css?v={{code_hash}}">
   <script src="https://cdn.jsdelivr.net/npm/@floating-ui/core@1.6.0"></script>
   <script src="https://cdn.jsdelivr.net/npm/@floating-ui/dom@1.6.3"></script>
   <script src="/base.js?v={{code_hash}}"></script>
</head>
<body>
% if no_sidebar:
<div id="contents" class="no-sidebar">
% else:
<div id="contents">
% endif
<header>
   <div id="menu-bar">
<a href="/">DHARMA</a>
<a id="menu-toggle"><i class="fa-solid fa-caret-down fa-fw"></i></a>
<ul id="menu" class="hidden">
   <li>
      <a href="/repositories">
      <i class="fa-brands fa-git-alt"></i> Repositories</a>
   </li>
   <li>
      <a href="{{url_for("show_catalog")}}">
      <i class="fa-regular fa-file-lines"></i> Texts</a>
   </li>
   <li class="submenu">
      <a>Conventions <i class="fa-solid fa-caret-down"></i></a>
      <ul class="hidden">
         <li><a href="/editorial-conventions">Editorial Conventions</a></li>
         <li><a href="/prosody">Prosodic Patterns</a></li>
      </ul>
   <li>
      <a href="/parallels">
      <i class="fa-solid fa-grip-lines-vertical"></i> Parallels</a>
   </li>
   <li class="submenu">
      <a>Project Internal <i class="fa-solid fa-caret-down"></i></a>
      <ul class="hidden">
         <li>
            <a href="{{url_for('show_texts_errors')}}">
            <i class="fa-solid fa-bug"></i> Errors</a>
         </li>
         <li>
            <a href="{{url_for('display_list')}}">Display List</a>
         </li>
      </ul>
   </li>
</ul>
   </div>
</header>
<div id="sidebar">
   <div id="toc-heading" class="toc-heading hidden">Contents</div>
   <nav id="toc"></nav>
   % block sidebar
   % endblock
</div>
<main>
<h1>
% block title
Untitled
% endblock
</h1>
% block body
% endblock
</main>
<footer>
<p><small>© <a href="https://dharma.hypotheses.org">ERC-DHARMA Project</a>, 2019-2024</small></p>
</footer>
</div>
<div id="tip-box" class="hidden">
   <div id="tip-contents"></div>
   <div id="tip-arrow"></div>
</div>
</body>
</html>
