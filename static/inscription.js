let displays = [
	["physical", "#phys-btn", "#phys"],
	["logical", "#log-btn", "#log"],
	["xml", "#xml-btn", "#xml"],
]
function switchDisplayTo(name) {
	for (let row of displays) {
		if (row[0] == name) {
			document.querySelector(row[1]).classList.add("active")
			document.querySelector(row[2]).style.display = "block"
		} else {
			document.querySelector(row[1]).classList.remove("active")
			document.querySelector(row[2]).style.display = "none"
		}
	}
}

window.addEventListener("load", function () {
	for (let row of displays) {
		document.querySelector(row[1]).onclick = function (ev) {
			ev.preventDefault()
			switchDisplayTo(row[0])
		}
	}
})
