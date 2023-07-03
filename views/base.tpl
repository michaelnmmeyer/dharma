<!doctype html>
<html lang="en">
<head>
   <title>{{title}}</title>
   <link rel="preconnect" href="https://fonts.googleapis.com">
   <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
   <link href="https://fonts.googleapis.com/css2?family=Noto+Sans:ital@0;1&display=swap" rel="stylesheet">
   <style>
   body {
      margin: 1rem;
      font-family: 'Noto Sans', sans-serif;
   }
   menu {
      padding: 0;
      display: flex;
      gap: 2rem;
      list-style: none;
      font-size: larger;
	}
	a {
	   text-decoration: none;
   }
   div.verse {
      margin-block-start: 0.3em;
      margin-block-end: 1em;
   }
   p.verse {
      /* Hanging indent */
      padding-left: 1rem ;
      text-indent: -1rem ;
      margin-block-start: 0em;
      margin-block-end: 0em;
   }
   </style>
</head>
<body>
   <menu class="body">
      <li><a href="/">Home</a></li>
      <li><a href="/commit-log">Commit Log</a></li>
      <li><a href="/texts">Texts</a></li>
      <li><a href="/parallels/verses">Parallel Verses</a></li>
   </menu>
   {{!base}}
</body>
</html>
