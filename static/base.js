const floatingUI = window.FloatingUIDOM

function unwrap(node) {
	node.replaceWith(...node.childNodes)
}

function getCSSVar(name) {
	return getComputedStyle(document.documentElement).getPropertyValue(name)
}

// menu

let menu = null
let menuIcon = null
let menuVisible = null

let submenu = null
let submenuVisible = null
let submenuContainer = null
let submenuCleanup = null
let submenuIcon = null

function initMenu() {
	menu = document.querySelector("#menu")
	menuVisible = !menu.classList.contains("hidden")
	menuIcon = document.querySelector("#menu-toggle i")
	submenu = document.querySelector("#submenu > ul")
	console.assert(submenu.classList.contains("hidden"))
	submenuVisible = false
	submenuContainer = document.querySelector("#submenu")
	submenuIcon = document.querySelector("#submenu > a > i")
	document.querySelector("#menu-toggle").addEventListener("click", toggleMenu, false)
	document.querySelector("#submenu > a").addEventListener("click", toggleSubmenu, false)
}

function showMenu() {
	console.assert(!menuVisible)
	menu.classList.remove("hidden")
	menuIcon.classList.remove("fa-caret-down")
	menuIcon.classList.add("fa-caret-up")
	menuVisible = true
}

function hideMenu() {
	console.assert(menuVisible)
	menu.classList.add("hidden")
	menuIcon.classList.remove("fa-caret-up")
	menuIcon.classList.add("fa-caret-down")
	menuVisible = false
}

function toggleMenu() {
	if (menuVisible)
		hideMenu()
	else
		showMenu()
}

function updateSubmenuPosition() {
	floatingUI.computePosition(submenuContainer, submenu, {
		placement: "bottom-end",
		middleware: [floatingUI.shift()]
	}).then(function ({x, y}) {
		submenu.style.top = `${y}px`,
		submenu.style.left = `${x}px`
	})
}

function showSubmenu() {
	console.assert(!submenuVisible)
	console.assert(!submenuCleanup)
	console.assert(submenu.classList.contains("hidden"))
	document.querySelector("#submenu").append(submenu)
	submenu.classList.remove("hidden")
	submenuCleanup = floatingUI.autoUpdate(submenuContainer, submenu,
		updateSubmenuPosition)
	submenuIcon.classList.remove("fa-caret-down")
	submenuIcon.classList.add("fa-caret-up")
	submenuVisible = true
}

function hideSubmenu() {
	console.assert(submenuVisible)
	console.assert(submenuCleanup)
	console.assert(!submenu.classList.contains("hidden"))
	submenu.classList.add("hidden")
	submenu.remove()
	submenuCleanup()
	submenuCleanup = null
	submenuIcon.classList.remove("fa-caret-up")
	submenuIcon.classList.add("fa-caret-down")
	submenuVisible = false
}

function toggleSubmenu() {
	if (submenuVisible)
		hideSubmenu()
	else
		showSubmenu()
}

window.addEventListener("load", function () {
	// Hide the submenu if the user clicks anywhere on the page.
	document.addEventListener("click", function (event) {
		if (submenu.classList.contains("hidden"))
			return
		if (submenuContainer.contains(event.target))
			return
		hideSubmenu()
	})
	initMenu()
})

// end menu






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
	popperInstance = Popper.createPopper(this, tipBox, {
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

let flashDuration = null

function highlightFragment(node) {
	node.classList.add("flash")
	setTimeout(function () {
		node.classList.remove("flash")
	}, flashDuration)
}

function handleClick(event) {
	if (!this.href)
		return
	let url = new URL(this.href)
	if (url.hash.length == 0)
		return
	if (url.origin != window.location.origin)
		return
	if (url.path != window.location.path)
		return
	let target = document.querySelector(url.hash)
	if (!target)
		return
	event.preventDefault()
	target.scrollIntoView()
	highlightFragment(target)
}

function initFlashing() {
	let t = getCSSVar("--flash-duration")
	flashDuration = parseInt(t)
	if (!t.endsWith("ms")) {
		// Assume in seconds
		flashDuration *= 1000
	}
	for (let node of document.querySelectorAll("a"))
		node.addEventListener("click", handleClick)
	let frag = window.location.hash
	if (!frag)
		return
	let target = document.querySelector(frag)
	if (!target)
		return
	target.scrollIntoView()
	highlightFragment(target)
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
		// Remove inner links
		for (let a of link.querySelectorAll("a[href]"))
			unwrap(a)
		li.appendChild(link)
		// TODO do something less stupid
		for (let display of displays) {
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
	document.querySelector("#toc-heading").classList.remove("hidden")
	TOCEntryToHTML(root, toc)
}

let displays = ["logical", "physical", "full", "xml"]
let currentDisplay = "logical"

function displayButton(name) {
	return document.querySelector("#" + name + "-btn")
}

function switchDisplayTo(name) {
	for (let display of displays) {
		if (display == name) {
			displayButton(display).classList.add("active")
		} else {
			displayButton(display).classList.remove("active")
		}
	}
	for (let node of document.querySelectorAll("[data-display]")) {
		if (node.dataset.display == name) {
			node.classList.remove("hidden")
		} else {
			node.classList.add("hidden")
		}
	}
	currentDisplay = name
}

function initDisplays() {
	for (let name of displays) {
		let button = displayButton(name)
		if (!button)
			continue
		button.addEventListener("click", function (event) {
			switchDisplayTo(name)
			event.preventDefault()
		})
	}
}

// Localize <time> nodes. The node initially contains the date in the server's
// time zone. We use the same format everywhere, on purpose, for simplicity,
// but we do use the user's local time zone when possible.
function localizeDate(node) {
	console.assert(node.localName == "time" && node.dateTime)
	let when = new Date(node.dateTime)
	let year = when.getFullYear()
	let month = new String(when.getMonth() + 1).padStart(2, "0")
	let day = new String(when.getDate()).padStart(2, "0")
	let hour = new String(when.getHours()).padStart(2, "0")
	let minute = new String(when.getMinutes()).padStart(2, "0")
	node.innerText = `${year}-${month}-${day} ${hour}:${minute}`
}
function localizeDates() {
	for (let node of document.querySelectorAll("time"))
		localizeDate(node)
}

window.addEventListener("load", function () {
	localizeDates()
	prepareTips()
	displayTOC()
	initDisplays()
	initFlashing()
})
