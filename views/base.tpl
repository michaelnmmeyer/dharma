<!doctype html>
<html lang="en">
<head>
   <title>{{title}}</title>
   <link rel="preconnect" href="https://fonts.googleapis.com">
   <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
   <link href="https://fonts.googleapis.com/css2?family=Gentium+Book+Plus:ital,wght@0,400;0,700;1,400;1,700&display=swap" rel="stylesheet">
   <style>
   body {
      margin: 1em auto;
      line-height: 1.34;
      padding: 0 1em;
      max-width: max-content;
      font-family: 'Gentium Book Plus', serif;
   }
   .body {
      margin: 1em auto;
      line-height: 1.34;
      padding: 0 1em;
      max-width: 40rem;
   }
   menu {
      display: flex;
      gap: 2rem;
      list-style: none;
      padding: 0;
      font-size: larger;
	}
	a {
	   text-decoration: none;
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
