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

function showTooltip() {
	// Make the tooltip visible
	tipBox.setAttribute("data-show", "");
	// Enable the event listeners
	popperInstance.setOptions((options) => ({
		...options,
		modifiers: [
			...options.modifiers,
			{ name: "eventListeners", enabled: true },
		],
	}));
	// Update its position
	popperInstance.update();
}

function hideTooltip() {
	// Hide the tooltip
	tipBox.removeAttribute("data-show");
	// Disable the event listeners
	popperInstance.setOptions((options) => ({
		...options,
		modifiers: [
			...options.modifiers,
			{ name: "eventListeners", enabled: false },
		],
	}));
}

function prepareTips() {
	tipBox = document.querySelector("#dh-tip-box")
	let tipContents = document.querySelector("#dh-tip-contents")
	console.assert(tipContents)
	for (let node of document.querySelectorAll("[data-tip]")) {
		node.classList.add("dh-tipped")
		node.onmouseover = function (e) {
			let tip = this.dataset.tip
			console.assert(tip)
			tipContents.innerHTML = tip
			popperInstance = createPopper(node, tipBox, {
				modifiers: [
					{
						name: "offset",
						options: {
							offset: [0, 8],
						},
					},
				],
			});
			showTooltip()
		}
		node.onmouseleave = function (e) {
			hideTooltip()
			popperInstance.destroy()
			popperInstance = null
		}
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
