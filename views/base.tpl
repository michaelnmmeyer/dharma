<!doctype html>
<html lang="en">
<head>
   <meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
   <title>{{title}}</title>
   <link rel="stylesheet" href="/fonts.css">
   <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
   <link rel="stylesheet" href="/base.css">
% if get('includes'):
   {{!includes}}
% end
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
<aside>
% if get('sidebar'):
{{!sidebar}}
% else:
Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
% end
</aside>
<main>
   {{!base}}
</main>
<footer>
<p>© <a href="https://dharma.hypotheses.org">ERC-DHARMA
Project</a>, 2019-2023</p>
</footer>
</div>

<script>
const menu = document.querySelector("menu");
/* Toggle mobile menu */
function toggleMenu() {
   if (menu.classList.contains("active")) {
      menu.classList.remove("active")
      // adds the menu (hamburger) icon
      document.querySelector("#toggle-menu a").innerHTML = "<i class='fa-solid fa-bars'></i>"
   } else {
      menu.classList.add("active")
      // adds the close (x) icon
      document.querySelector("#toggle-menu a").innerHTML = "<i class='fa-solid fa-times'></i>"
   }
}
document.querySelector("#toggle-menu").addEventListener("click", toggleMenu, false);

const toc = document.querySelector("aside");
function toggleTOC() {
   if (toc.classList.contains("active")) {
      toc.classList.remove("active")
      document.querySelector("#toggle-toc a").innerHTML = "<i class='fa-solid fa-table-list'></i>"
   } else {
      toc.classList.add("active")
      document.querySelector("#toggle-toc a").innerHTML = "<i class='fa-solid fa-times'></i>"
   }
}
document.querySelector("#toggle-toc").addEventListener("click", toggleTOC, false);


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
