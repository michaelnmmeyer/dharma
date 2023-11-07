<!doctype html>
<html lang="en">
<head>
   <meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
   <title>{{title}}</title>
   <link rel="preconnect" href="https://fonts.googleapis.com">
   <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
   <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Mono:wght@300;400;500;600;700&family=Noto+Serif+Grantha&family=Noto+Serif:ital,wght@0,100;0,200;0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,100;1,200;1,300;1,400;1,500;1,600;1,700;1,800;1,900&display=swap" rel="stylesheet">
   <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.13.0/css/all.min.css">
   <link rel="stylesheet" href="/base.css">
% if get('includes'):
   {{!includes}}
% end
</head>
<body>
   <header>
      <menu>
         <li class="logo"><a href="/">DHARMA</a></li>
         <li class="toggle"><a href="#"><i class="fas fa-bars"></i></a></li>
         <li class="item"><a href="/commits">Commits</a></li>
         <li class="item"><a href="/texts">Texts</a></li>
         <li class="item"><a href="/catalog">Catalog</a></li>
         <li class="item"><a href="/parallels">Parallels</a></li>
         <li class="item"><a href="/display">🚧 Display</a></li>
         <li class="item"><a href="/documentation">Documentation</a>
      </menu>
   </header>
   <main>
      {{!base}}
   </main>
   <footer>
   </footer>

<script>
const toggle = document.querySelector(".toggle");
const menu = document.querySelector("menu");
/* Toggle mobile menu */
function toggleMenu() {
    if (menu.classList.contains("active")) {
        menu.classList.remove("active");

        // adds the menu (hamburger) icon
        toggle.querySelector("a").innerHTML = "<i class='fas fa-bars'></i>";
    } else {
        menu.classList.add("active");

        // adds the close (x) icon
        toggle.querySelector("a").innerHTML = "<i class='fas fa-times'></i>";
    }
}
/* Event Listener */
toggle.addEventListener("click", toggleMenu, false);

for (let node of document.querySelectorAll("[data-href]")) {
   node.style.cursor = "pointer"
   node.addEventListener("click", function() {
      let href = this.getAttribute('data-href')
      window.location.href = href
   });
}

</script>
</body>
</html>
