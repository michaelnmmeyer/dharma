<!doctype html>
<html lang="en">
<head>
   <meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
   <title>{{title}}</title>
   <link rel="preconnect" href="https://fonts.googleapis.com">
   <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
   <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+Grantha&family=Noto+Serif:ital,wght@0,100;0,200;0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,100;1,200;1,300;1,400;1,500;1,600;1,700;1,800;1,900&display=swap" rel="stylesheet">
   <style>
   body {
      margin: 1rem;
      font-family: 'Noto Serif', 'Noto Serif Grantha', serif;
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
      margin-block-start: 0.3em; /* not good! */
      margin-block-end: 1em;
   }
   p.verse {
      /* Hanging indent */
      padding-left: 1rem ;
      text-indent: -1rem ;
      margin-block-start: 0em;
      margin-block-end: 0em;
   }
   table {
      border-collapse: collapse;
   }
   td, th {
      padding: 0.4em;
   }
   table tr:nth-child(odd) {
      background-color: #eff0f1;
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
