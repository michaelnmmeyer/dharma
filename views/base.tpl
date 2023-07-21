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
      font-family: 'Noto Serif', 'Noto Serif Grantha', serif;
   }
   .whole {
      max-width: max-content;
      margin: auto;
   }
   .body {
      max-width: 40em;
      margin: 1em auto;
   }
   menu {
      padding: 0;
      display: flex;
      gap: 2rem;
      list-style: none;
      font-size: larger;
	}
	p {
	   text-align: justify;
	}
	a {
	   text-decoration: none;
   }
   div.verse {
      /* Same properties as a normal <p> */
      /* margin-block-start: 1em;
      margin-block-end: 1em; */
   }
   div.verse > p {
      /* No space between hemistiches */
      margin-block-start: 0em;
      margin-block-end: 0em;
      /* Hanging indent */
      padding-left: 2em;
      text-indent: -2em;
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
   <div class="whole">
   <div class="body">
   <menu>
      <li><a href="/">Home</a></li>
      <li><a href="/commit-log">Commit Log</a></li>
      <li><a href="/texts">Texts</a></li>
      <li><a href="/parallels">Parallels</a></li>
   </menu>
   </div>
   {{!base}}
   </div>
</body>
</html>
