function init() {
	let textDisp = document.querySelector(".dh-ed").style.display
	let codeDisp = document.querySelector(".dh-xml").style.display
	document.querySelector(".dh-xml").style.display = "none"
	document.querySelector("#phys-btn").onclick = function(node) {
		document.querySelector(".dh-ed").style.display = textDisp
		document.querySelector(".dh-xml").style.display = "none"
		document.querySelector("#ins-display")["href"] = "/ins-phys.css"
	}
	document.querySelector("#log-btn").onclick = function(node) {
		document.querySelector(".dh-ed").style.display = textDisp
		document.querySelector(".dh-xml").style.display = "none"
		document.querySelector("#ins-display")["href"] = "/ins-log.css"
	}
	document.querySelector("#xml-btn").onclick = function(node) {
		document.querySelector(".dh-ed").style.display = "none"
		document.querySelector(".dh-xml").style.display = codeDisp
	}
}

window.onload = function(ev) {
	init()
}
