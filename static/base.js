function toggleMenu() {
	let menu = document.querySelector("menu")
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

function toggleTOC() {
	let toc = document.querySelector("aside")
	if (toc.classList.contains("active")) {
		toc.classList.remove("active")
		document.querySelector("#toggle-toc a").innerHTML = "<i class='fa-solid fa-table-list'></i>"
	} else {
		toc.classList.add("active")
		document.querySelector("#toggle-toc a").innerHTML = "<i class='fa-solid fa-times'></i>"
	}
}

function flashTarget() {
	if (!this["href"]) {
		return
	}
	let url = new URL(this["href"])
	let node = document.querySelector(url.hash)
	node.classList.add("dh-flash")
	setTimeout(function () {
		node.classList.remove("dh-flash")
	}, 2000)
}

window.addEventListener("load", function () {
	document.querySelector("#toggle-menu").addEventListener("click", toggleMenu, false)
	document.querySelector("#toggle-toc").addEventListener("click", toggleTOC, false)
	for (let node of document.querySelectorAll("[data-href]")) {
		node.style.cursor = "pointer"
		node.addEventListener("click", function() {
			let href = this.getAttribute('data-href')
			window.location.href = href
		})
	}
	for (let node of document.querySelectorAll("aside a")) {
		node.addEventListener("click", flashTarget)
	}
})
