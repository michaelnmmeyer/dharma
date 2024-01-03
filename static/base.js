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

// See the popper doc + https://codepen.io/jsonc/pen/LYbyyaM
let popperInstance = null
let tipBox = null

function addTooltip(e) {
	let tip = this.dataset.tip
	let tipContents = document.querySelector("#dh-tip-contents")
	if (popperInstance) {
		let have = tipContents.innerHTML
		tipContents.innerHTML = tip + " | " + have
		this.owning = false
		return
	}
	tipContents.innerHTML = tip
	this.owning = true
	this.classList.add("dh-tipped")
	tipBox.setAttribute("data-show", "")
	popperInstance = createPopper(this, tipBox, {
		modifiers: [{
			name: "offset",
			options: {
				offset: [0, 8],
			},
		}, {
			name: "eventListeners",
			enabled: true,
		}],
	})
	popperInstance.update()
}

function removeTooltip(e) {
	if (!this.owning)
		return
	this.classList.remove("dh-tipped")
	tipBox.removeAttribute("data-show")
	let tipContents = document.querySelector("#dh-tip-contents")
	tipContents.innerHTML = ""
	popperInstance.destroy()
	popperInstance = null
}

function prepareTips() {
	tipBox = document.querySelector("#dh-tip-box")
	let tipContents = document.querySelector("#dh-tip-contents")
	console.assert(tipContents)
	for (let node of document.querySelectorAll("[data-tip]")) {
		node.addEventListener("mouseover", addTooltip)
		node.addEventListener("mouseout", removeTooltip)
	}
}

function flashTarget() {
	if (!this["href"]) {
		return
	}
	let url = new URL(this["href"])
	let node = document.querySelector(url.hash)
}

function highlightFragment() {
	let hash = window.location.hash
	if (!hash)
		return
	let node = document.querySelector(hash)
	if (!node)
		return
	node.classList.add("dh-flash")
	setTimeout(function () {
		node.classList.remove("dh-flash")
	}, 2000)
}

window.addEventListener("load", function () {
	prepareTips()
	highlightFragment()
})

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
	for (let node of document.querySelectorAll("h1, h2, h3, h4, h5, h6")) {
		let id = node.id
		if (id) {
			let a = document.createElement("a")
			a.href = "#" + id
			node.appendChild(a)
		}
	}
})
