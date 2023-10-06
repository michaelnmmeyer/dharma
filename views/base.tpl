<!doctype html>
<html lang="en">
<head>
   <meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
   <title>{{title}}</title>
   <link rel="preconnect" href="https://fonts.googleapis.com">
   <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
   <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Mono:wght@300;400;500;600;700&family=Noto+Serif+Grantha&family=Noto+Serif:ital,wght@0,100;0,200;0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,100;1,200;1,300;1,400;1,500;1,600;1,700;1,800;1,900&display=swap" rel="stylesheet">
   <link rel="stylesheet" href="/base.css">
% if get('includes'):
   {{!includes}}
% end
</head>
<body>
<div class="whole">
   <header>
      <menu>
         <li><a href="/">Home</a></li>
         <li><a href="/commit-log">Commits</a></li>
         <li><a href="/texts">Texts</a></li>
         <li><a href="/catalog">Catalog</a></li>
         <li><a href="/parallels">Parallels</a></li>
         <li><a href="/display">🚧 Display</a></li>
         <li><a href="/documentation">Documentation</a>
      </menu>
   </header>
   <main>
      {{!base}}
   </main>
   <footer>
   </footer>
</div>
</body>
</html>
