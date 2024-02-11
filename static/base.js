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

function addTooltip() {
	let tip = this.dataset.tip
	let tipContents = document.querySelector("#tip-contents")
	if (popperInstance) {
		let have = tipContents.innerHTML
		tipContents.innerHTML = tip + " | " + have
		this.owning = false
		return
	}
	tipContents.innerHTML = tip
	this.owning = true
	this.classList.add("tipped")
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

function removeTooltip() {
	if (!this.owning)
		return
	this.classList.remove("tipped")
	tipBox.removeAttribute("data-show")
	let tipContents = document.querySelector("#tip-contents")
	tipContents.innerHTML = ""
	popperInstance.destroy()
	popperInstance = null
}

function prepareTips() {
	tipBox = document.querySelector("#tip-box")
	let tipContents = document.querySelector("#tip-contents")
	console.assert(tipContents)
	for (let node of document.querySelectorAll("[data-tip]")) {
		node.addEventListener("mouseover", addTooltip)
		node.addEventListener("mouseout", removeTooltip)
	}
}

function flashTarget() {
	if (!this.href)
		return
	let url = new URL(this.href)
	if (url.origin != window.location.origin)
		return
	if (url.path != window.location.path)
		return
	highlightFragment(url)
}

var flashDuration

function highlightFragment(url) {
	let hash = url.hash
	if (!hash)
		return
	let node = document.querySelector(hash)
	if (!node)
		return
	node.classList.add("flash")
	setTimeout(function () {
		node.classList.remove("flash")
	}, 2000)
}

function makeTOC() {
	let toc = document.getElementById("toc")
	if (!toc)
		return
	let headings = document.body.querySelectorAll("h2, h3, h4, h5, h6")
	for (let i = 0; i < headings.length; i++) {
		let heading = headings[i]
		let anchor = document.createElement("a")
		anchor.setAttribute("name", "toc" + i)
		anchor.setAttribute("id", "toc" + i)
		let link = document.createElement("a")
		link.setAttribute("href", "#toc" + i)
		link.textContent = heading.textContent
		let div = document.createElement("div")
		div.setAttribute("class", "toc-" + heading.tagName.toLowerCase());
		div.appendChild(link)
		toc.appendChild(div)
		heading.parentNode.insertBefore(anchor, heading)
	}
}

window.addEventListener("load", function () {
	prepareTips()
	let t = getComputedStyle(document.documentElement).getPropertyValue("--flash-duration")
	flashDuration = parseInt(t)
	if (!t.endsWith("ms")) {
		// Assume in seconds
		flashDuration *= 1000
	}
	highlightFragment(window.location)
	for (let node of document.querySelectorAll("a"))
		node.addEventListener("click", flashTarget)
	makeTOC()
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
