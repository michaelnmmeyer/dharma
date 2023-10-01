function resetButtonsBackground(val) {
	document.querySelector("#phys-btn").style["background-color"] = val
	document.querySelector("#log-btn").style["background-color"] = val
	document.querySelector("#xml-btn").style["background-color"] = val
}

function init() {
	let textDisp = document.querySelector(".dh-ed").style.display
	let codeDisp = document.querySelector(".dh-xml").style.display
	let btnBackground = document.querySelector("#phys-btn").style["background-color"]
	document.querySelector(".dh-xml").style.display = "none"
	document.querySelector("#phys-btn").onclick = function(ev) {
		document.querySelector(".dh-ed").style.display = textDisp
		document.querySelector(".dh-xml").style.display = "none"
		document.querySelector("#ins-display")["href"] = "/ins-phys.css"
		resetButtonsBackground(btnBackground)
		document.querySelector("#phys-btn").style["background-color"] = "red"
	}
	document.querySelector("#log-btn").onclick = function(ev) {
		document.querySelector(".dh-ed").style.display = textDisp
		document.querySelector(".dh-xml").style.display = "none"
		document.querySelector("#ins-display")["href"] = "/ins-log.css"
		resetButtonsBackground(btnBackground)
		document.querySelector("#log-btn").style["background-color"] = "red"
	}
	document.querySelector("#xml-btn").onclick = function(ev) {
		document.querySelector(".dh-ed").style.display = "none"
		document.querySelector(".dh-xml").style.display = codeDisp
		resetButtonsBackground(btnBackground)
		document.querySelector("#xml-btn").style["background-color"] = "red"
	}
	document.querySelector("#phys-btn").style["background-color"] = "red"
}

window.onload = function(ev) {
	init()
}
