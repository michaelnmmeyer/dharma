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
	let parser = new DOMParser()
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
			if (!tip)
				tip = e.srcElement.parentNode.dataset.tip
			if (!tip)
				return
			console.log(tip);
			tipBox.innerHTML = tip
			tipBox.style.display = "block"
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

function flashNode(node) {
	node.classList.add("dh-flash")
	setTimeout(function () {
		node.classList.remove("dh-flash")
	}, 3000)
}

function init() {
	prepareTips()
	for (let node of document.querySelectorAll(".dh-bib-ref a")) {
		node.onclick = function (e) {
			let url = new URL(e.srcElement["href"])
			let ent = document.querySelector(url.hash)
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
