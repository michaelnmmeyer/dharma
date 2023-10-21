let displays = [
	["physical", "#phys-btn", "#dh-phys"],
	["logical", "#log-btn", "#dh-log"],
	["xml", "#xml-btn", "#dh-xml"],
]
function switchDisplayTo(name) {
	for (row of displays) {
		if (row[0] == name) {
			document.querySelector(row[1]).classList.add("dh-active")
			document.querySelector(row[2]).style.display = "block"
		} else {
			document.querySelector(row[1]).classList.remove("dh-active")
			document.querySelector(row[2]).style.display = "none"
		}
	}
}

function init() {
	for (row of displays) {
		let name = row[0]
		document.querySelector(row[1]).onclick = function (ev) {
			ev.preventDefault()
			switchDisplayTo(name)
		}
	}
}

window.onload = function(ev) {
	init()
}
