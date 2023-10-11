var buttonDfltBg
const buttonActiveBg = "red"

function resetButtonsBackground() {
	document.querySelector("#phys-btn").style["background-color"] = buttonDfltBg
	document.querySelector("#log-btn").style["background-color"] = buttonDfltBg
	document.querySelector("#xml-btn").style["background-color"] = buttonDfltBg
}

function init() {
	buttonDfltBg = document.querySelector("#phys-btn").style["background-color"]
	let logDisp = document.querySelector("#dh-log").style
	let physDisp = document.querySelector("#dh-phys").style
	let xmlDisp = document.querySelector("#dh-xml").style
	document.querySelector("#log-btn").onclick = function(ev) {
		logDisp.display = "block"
		physDisp.display = "none"
		xmlDisp.display = "none"
		resetButtonsBackground()
		document.querySelector("#log-btn").style["background-color"] = buttonActiveBg
	}
	document.querySelector("#phys-btn").onclick = function(ev) {
		logDisp.display = "none"
		physDisp.display = "initial"
		xmlDisp.display = "none"
		resetButtonsBackground()
		document.querySelector("#phys-btn").style["background-color"] = buttonActiveBg
	}
	document.querySelector("#xml-btn").onclick = function(ev) {
		logDisp.display = "none"
		physDisp.display = "none"
		xmlDisp.display = "block"
		resetButtonsBackground()
		document.querySelector("#xml-btn").style["background-color"] = buttonActiveBg
	}
	document.querySelector("#log-btn").style["background-color"] = buttonActiveBg
}

window.onload = function(ev) {
	init()
}
