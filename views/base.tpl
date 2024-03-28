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
   <script src="https://unpkg.com/@popperjs/core@2"></script>
   <script src="/base.js?v={{code_hash}}"></script>
</head>
<body>
<div id="contents">
<header>
   <menu>
      <li class="toggle" id="toggle-menu"><a><i class="fa-solid fa-bars"></i></a></li>
      <li class="logo"><a href="/">DHARMA</a></li>
      <li class="toggle" id="toggle-toc"><a><i class="fa-solid fa-table-list"></i></a></li>
      <li class="item"><a href="/repositories"><i class="fa-brands fa-git-alt"></i> Repositories</a></li>
      <li class="item"><a href="{{url_for("show_catalog")}}"><i class="fa-regular fa-file-lines"></i> Texts</a></li>
      <li class="item"><a href="{{url_for("show_editorial_conventions")}}">Editorial Conventions</a></li>
      <li class="item"><a href="/parallels"><i class="fa-solid fa-grip-lines-vertical"></i>
      Parallels</a></li>
      <li class="item" id="submenu-button"><a>Project Internal <i class="fa-solid fa-caret-down"></i></a></li>
   </menu>
</header>
<aside>
   <div id="toc-heading" class="toc-heading hidden">Contents</div>
   <nav id="toc"></nav>
% block sidebar
% endblock
</aside>
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
<div id="tip-box">
   <div id="tip-contents"></div>
   <div id="tip-arrow" data-popper-arrow></div>
</div>
<div id="submenu" class="hidden">
<ul>
<li class="item">
   <a href="{{url_for('show_texts_errors')}}"><i class="fa-solid fa-bug"></i> Errors</a>
</li>
<li class="item">
   <a href="/documentation">
   <i class="fa-regular fa-circle-question"></i>
   Technical Documentation
   </a>
</li>
<li class="item">
   <a href="{{url_for('display_list')}}">Display List</a>
</li>
</ul>
</div>
</body>
</html>
