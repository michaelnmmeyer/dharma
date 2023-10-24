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

function prepareTips() {
	let tipBox = document.querySelector("#dh-tip-box")
	for (let node of document.querySelectorAll("[data-tip]")) {
		node.classList.add("dh-tipped")
		node.onmouseover = function (e) {
			let rec = e.srcElement.getBoundingClientRect()
			let tip = e.srcElement.dataset.tip
			// Special case for:
			// 	<span class="dh-symbol dh-tipped" data-tip="....>
			// 		<img alt="spiralR" class="dh-svg" src="/gaiji/spiralR.svg">
			// 	</span>
			// In this case, e.srcElement is <img>, not <span>, for some reason.
			if (tip === undefined) {
				tip = e.srcElement.parentNode.dataset.tip
			}
			tipBox.innerText = tip
			tipBox.style.display = "block"
			console.log(tipBox.width + " " + tipBox.height)
			let x = e.srcElement.offsetLeft
			let y = e.srcElement.offsetTop + e.srcElement.offsetHeight
			tipBox.style.top = y + "px"
			tipBox.style.left = x + "px"
		}
		node.onmouseleave = function (e) {
			tipBox.style.display = "none"
		}
	}
}

function init() {
	prepareTips()
	for (let row of displays) {
		document.querySelector(row[1]).onclick = function (ev) {
			ev.preventDefault()
			switchDisplayTo(row[0])
		}
	}
}

window.onload = function(ev) {
	init()
}
