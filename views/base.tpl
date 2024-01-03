<!doctype html>
<html lang="en">
<head>
   <meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
   <title>{{title}}</title>
   <link rel="stylesheet" href="/fonts.css">
   <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
   <link rel="stylesheet" href="/base.css">
   <script src="/pack.js"></script>
   <script src="/base.js"></script>
   {{!get('includes', '')}}
</head>
<body>

<div id="contents">
<header>
   <menu>
      <li class="toggle" id="toggle-menu"><a><i class="fa-solid fa-bars"></i></a></li>
      <li class="logo"><a href="/">DHARMA</a></li>
      <li class="toggle" id="toggle-toc"><a><i class="fa-solid fa-table-list"></i></a></li>
      <li class="item"><a href="/commits"><i class="fa-brands fa-github"></i> Commits</a></li>
      <li class="item"><a href="/texts"><!--<i class="fa-solid fa-bug"></i>--> Texts</a></li>
      <li class="item"><a href="/catalog"><!--<i class="fa-solid
      fa-magnifying-glass"></i>--> Catalog</a></li>
      <li class="item"><a href="/parallels"><!--<i class="fa-solid fa-chart-simple"></i>-->
      Parallels</a></li>
      <li class="item"><a href="/display">🚧 Display</a></li>
      <li class="item"><a href="/bibliography"><i class="fa-solid fa-quote-left"></i> Bibliography</a></li>
      <li class="item"><a href="/documentation"><i class="fa-regular fa-circle-question"></i> Documentation</a>
   </menu>
</header>
<aside>{{!get('sidebar', '')}}</aside>
<main>{{!base}}</main>
<footer>
<p>© <a href="https://dharma.hypotheses.org">ERC-DHARMA Project</a>, 2019-2024</p>
</footer>
</div>

<div id="dh-tip-box">
   <div id="dh-tip-contents"></div>
   <div id="dh-tip-arrow" data-popper-arrow></div>
</div>

</body>
</html>
