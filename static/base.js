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
let menuContainer = null

let submenu = null
let submenus = []

class Submenu {

	constructor(node) {
		this.container = node
		this.submenu = node.querySelector("ul")
		this.submenu.style["min-width"] = getComputedStyle(this.container).getPropertyValue("width")
		console.assert(this.submenu.classList.contains("hidden"))
		this.visible = false
		this.button = node.querySelector("a")
		this.icon = this.button.querySelector("i")
		this.button.addEventListener("click", () => {
			this.toggle()
		}, false)
		this.cleanup = null
	}

	updatePosition() {
		floatingUI.computePosition(this.container, this.submenu, {
			placement: "bottom-end",
			middleware: [floatingUI.shift()]
		}).then(({x, y}) => {
			this.submenu.style.top = `${y}px`,
			this.submenu.style.left = `${x}px`
		})
	}

	show() {
		console.assert(!this.visible)
		console.assert(!this.cleanup)
		console.assert(this.submenu.classList.contains("hidden"))
		this.container.append(this.submenu)
		this.submenu.classList.remove("hidden")
		this.cleanup = floatingUI.autoUpdate(this.container,
			this.submenu, () => {this.updatePosition()})
		this.icon.classList.remove("fa-caret-down")
		this.icon.classList.add("fa-caret-up")
		this.visible = true
		submenu = this
	}

	hide() {
		console.assert(this.visible)
		console.assert(this.cleanup)
		console.assert(!this.submenu.classList.contains("hidden"))
		this.submenu.classList.add("hidden")
		this.submenu.remove()
		this.cleanup()
		this.cleanup = null
		this.icon.classList.remove("fa-caret-up")
		this.icon.classList.add("fa-caret-down")
		this.visible = false
		submenu = null
	}

	toggle() {
		if (submenu && submenu !== this) {
			submenu.hide()
		}
		if (this.visible)
			this.hide()
		else
			this.show()
	}
}

function initMenu() {
	menu = document.querySelector("#menu")
	menuVisible = !menu.classList.contains("hidden")
	menuIcon = document.querySelector("#menu-toggle i")
	menuContainer = document.querySelector("menu")
	for (let node of menu.querySelectorAll(".submenu"))
		submenus.push(new Submenu(node))
	document.querySelector("#menu-toggle").addEventListener("click", toggleMenu, false)
}

function showMenu() {
	console.assert(!menuVisible)
	console.assert(menu.classList.contains("hidden"))
	menu.classList.remove("hidden")
	menuIcon.classList.remove("fa-caret-down")
	menuIcon.classList.add("fa-caret-up")
	menuVisible = true
}

function hideMenu() {
	console.assert(menuVisible)
	console.assert(!menu.classList.contains("hidden"))
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

window.addEventListener("load", function () {
	// Hide the submenu if the user clicks anywhere on the page.
	document.addEventListener("click", function (event) {
		if (menuVisible && !menuContainer.contains(event.target))
			hideMenu()
		if (submenu && !submenu.container.contains(event.target)) {
			submenu.hide()
			submenu = null
		}
	})
	initMenu()
	let sidebar = document.querySelector("#sidebar")
	let sidebarClick = document.querySelector("#sidebar-interact")
	sidebarClick.addEventListener("click", function () {
		if (sidebar.style.display == "none")
			sidebar.style.display = "flex"
		else
			sidebar.style.display = "none"
	})
})

// end menu





let tipped = null
let tipBox = null
let tipContents = null
let tipCleanup = null
let tipArrow = null

function addTooltip() {
	let node = this
	let tip = node.dataset.tip
	if (tipped) {
		let have = tipContents.innerHTML
		tipContents.innerHTML = tip + " | " + have
		return
	}
	tipped = node
	tipContents.innerHTML = tip
	node.classList.add("tipped")
	tipBox.classList.remove("hidden")
	document.body.append(tipBox)
	tipCleanup = floatingUI.autoUpdate(tipped, tipBox, updateTooltipPosition)
}

function updateTooltipPosition() {
	floatingUI.computePosition(tipped, tipBox, {
		placement: "bottom",
		middleware: [
			floatingUI.offset(10),
			floatingUI.flip(),
			floatingUI.shift({padding: 10}),
			floatingUI.arrow({element: tipArrow})
		],
	}).then(({x, y, placement, middlewareData}) => {
		Object.assign(tipBox.style, {
			left: `${x}px`,
			top: `${y}px`,
		})
		const {x: arrowX, y: arrowY} = middlewareData.arrow;

		const staticSide = {
			top: ["bottom", "border-bottom-width", "border-right-width"],
			right: ["left", "border-bottom-width", "border-left-width"],
			bottom: ["top", "border-top-width", "border-left-width"],
			left: ["right", "border-top-width", "border-right-width"],
		}[placement.split("-")[0]]


		Object.assign(tipArrow.style, {
			left: arrowX != null ? `${arrowX}px` : "",
			top: arrowY != null ? `${arrowY}px` : "",
			right: "",
			bottom: "",
			[staticSide[0]]: "-6px",
			["border-width"]: "",
			[staticSide[1]]: "2px",
			[staticSide[2]]: "2px",
		})
	})
}
function removeTooltip() {
	let node = this
	if (node !== tipped)
		return
	tipped.classList.remove("tipped")
	tipBox.classList.add("hidden")
	tipContents.innerHTML = ""
	tipped = null
	tipBox.remove()
	tipCleanup()
	tipCleanup = null
}

function prepareTips() {
	tipBox = document.querySelector("#tip-box")
	tipContents = document.querySelector("#tip-contents")
	tipArrow = document.querySelector("#tip-arrow")
	tipBox.remove()
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
		// Prevent the button for collapsing the apparatus from
		// appearing in the TOC
		icon = link.querySelector("i")
		if (icon)
			icon.remove()
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
	let toc = document.querySelector("#toc")
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

function prepareCollapsible() {
	for (let node of document.querySelectorAll(".collapsible")) {
		node.addEventListener("click", function() {
			let content = this.nextElementSibling;
			let icon = this.querySelector("i")
			if (content.classList.contains("hidden")) {
				content.classList.remove("hidden")
				content.style.maxHeight = content.scrollHeight + "px"
				icon.classList.remove("fa-angles-up")
				icon.classList.add("fa-angles-down")
			} else {
				content.classList.add("hidden")
				content.style.maxHeight = null
				icon.classList.remove("fa-angles-down")
				icon.classList.add("fa-angles-up")
			}
		});
	}
}

window.addEventListener("load", function () {
	localizeDates()
	prepareTips()
	displayTOC()
	initDisplays()
	initFlashing()
	prepareCollapsible()
})
