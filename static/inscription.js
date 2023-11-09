let displays = [
	["physical", "#phys-btn", "#dh-phys"],
	["logical", "#log-btn", "#dh-log"],
	["xml", "#xml-btn", "#dh-xml"],
]
function switchDisplayTo(name) {
	for (let row of displays) {
		if (row[0] == name) {
			document.querySelector(row[1]).classList.add("dh-active")
			document.querySelector(row[2]).style.display = "block"
		} else {
			document.querySelector(row[1]).classList.remove("dh-active")
			document.querySelector(row[2]).style.display = "none"
		}
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

function flashNode(node) {
	node.classList.add("dh-flash")
	setTimeout(function () {
		node.classList.remove("dh-flash")
	}, 2000)
}

function init() {
	prepareTips()
	for (let node of document.querySelectorAll("a.dh-bib-ref, a.dh-note-ref")) {
		if (!node["href"])
			continue
		node.onclick = function (e) {
			let url = new URL(this["href"])
			let ent = document.querySelector(url.hash)
			console.log(url);
			flashNode(ent)
		}
	}
	for (let row of displays) {
		document.querySelector(row[1]).onclick = function (ev) {
			ev.preventDefault()
			switchDisplayTo(row[0])
		}
	}
}

window.onload = function () {
	init()
}
