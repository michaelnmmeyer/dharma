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

let flashDuration = null

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
	}, flashDuration)
}

function popTOCStack(stack, level) {
	while (stack.length >= level) {
		let child = stack.pop()
		let parent = stack[stack.length - 1]
		if (!parent.children)
			parent.children = []
		parent.children.push(child)
	}
}

function makeTOC() {
	let headings = document.body.querySelectorAll("h2, h3, h4, h5")
	let stack = [{"children": []}]
	for (let heading of headings) {
		let level = parseInt(heading.tagName.substring(1))
		popTOCStack(stack, level)
		while (stack.length < level - 1)
			stack.push({})
		stack.push({"heading": heading})
	}
	popTOCStack(stack, 2)
	return stack[0]
}

let idGenerator = 0

function TOCEntryToHTML(entry, root) {
	let li = root || document.createElement("li")
	let heading = entry.heading
	if (heading) {
		let link = document.createElement("a")
		link.classList.add("nav-link")
		let target = heading.getAttribute("id")
		if (!target) {
			idGenerator++
			target = "toc" + idGenerator
			heading.setAttribute("id", target)
		}
		link.setAttribute("href", "#" + target)
		link.innerHTML = heading.innerHTML
		li.appendChild(link)
		// TODO do something less stupid
		for (let display of ["logical", "physical", "full", "xml"]) {
			let tmp = document.querySelector("#" + display)
			if (tmp && tmp.contains(heading)) {
				li.dataset.display = display
				if (display == currentDisplay) {
					li.classList.remove("hidden")
				} else {
					li.classList.add("hidden")
				}
			}
		}
	}
	let children = entry.children
	if (children) {
		let ul = document.createElement("ul")
		for (let child of children)
			ul.appendChild(TOCEntryToHTML(child))
		li.appendChild(ul)
	}
	return li
}

function displayTOC() {
	let toc = document.getElementById("toc")
	if (!toc)
		return
	let root = makeTOC()
	if (root.children.length == 0)
		return
	document.querySelector("#toc-heading").style.display = "block"
	TOCEntryToHTML(root, toc)
}

window.addEventListener("load", function () {
	prepareTips()
	displayTOC()
	let t = getComputedStyle(document.documentElement).getPropertyValue("--flash-duration")
	flashDuration = parseInt(t)
	if (!t.endsWith("ms")) {
		// Assume in seconds
		flashDuration *= 1000
	}
	highlightFragment(window.location)
	for (let node of document.querySelectorAll("a"))
		node.addEventListener("click", flashTarget)
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
