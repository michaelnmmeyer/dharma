<!doctype html>
<html lang="en">
<head>
   <meta charset="utf-8">
   <meta name="viewport" content="width=device-width, initial-scale=1">
   <title>
   % block title
   % endblock
   </title>
   <link rel="stylesheet" href="{{root}}/fonts.css">
   <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
   <link rel="stylesheet" href="{{root}}/base.css">
   <script src="{{root}}/pack.js"></script>
   <script src="{{root}}/base.js"></script>
</head>
<body>

<div id="contents">
<header>
   <menu>
      <li class="toggle" id="toggle-menu"><a><i class="fa-solid fa-bars"></i></a></li>
      <li class="logo"><a href="{{root}}/">DHARMA</a></li>
      <li class="toggle" id="toggle-toc"><a><i class="fa-solid fa-table-list"></i></a></li>
      <li class="item"><a href="{{root}}/repositories"><i class="fa-brands fa-git-alt"></i> Repositories</a></li>
      <li class="item"><a href="{{root}}/texts"><i class="fa-solid fa-bug"></i> Texts</a></li>
      <li class="item"><a href="{{root}}/catalog"><i class="fa-solid
      fa-magnifying-glass"></i> Catalog</a></li>
      <li class="item"><a href="{{root}}/parallels"><i class="fa-solid fa-grip-lines-vertical"></i>
      Parallels</a></li>
      <li class="item"><a href="{{root}}/bibliography"><i class="fa-solid fa-quote-left"></i> Bibliography</a></li>
      <li class="item"><a href="{{root}}/documentation"><i class="fa-regular fa-circle-question"></i> Documentation</a>
   </menu>
</header>
<aside>
   <div id="toc-heading" class="toc-heading hidden">Contents</div>
   <nav id="toc"></nav>
</aside>
<main>
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

</body>
</html>
