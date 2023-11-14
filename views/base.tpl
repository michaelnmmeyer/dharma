<!doctype html>
<html lang="en">
<head>
   <meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
   <title>{{title}}</title>
   <link rel="stylesheet" href="/fonts.css">
   <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
   <link rel="stylesheet" href="/base.css">
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
      <li class="item"><a href="/commits">Commits</a></li>
      <li class="item"><a href="/texts">Texts</a></li>
      <li class="item"><a href="/catalog">Catalog</a></li>
      <li class="item"><a href="/parallels">Parallels</a></li>
      <li class="item"><a href="/display">🚧 Display</a></li>
      <li class="item"><a href="/documentation">Documentation</a>
   </menu>
</header>
<aside>{{!get('sidebar', '')}}</aside>
<main>{{!base}}</main>
<footer>
<p>© <a href="https://dharma.hypotheses.org">ERC-DHARMA Project</a>, 2019-2023</p>
</footer>
</div>
</body>
</html>
