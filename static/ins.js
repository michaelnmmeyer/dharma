function init() {
	document.querySelector("#phys-btn").onclick = function(node) {
		document.querySelector("#ins-display")["href"] = "/ins-phys.css"
	}
	document.querySelector("#log-btn").onclick = function(node) {
		document.querySelector("#ins-display")["href"] = "/ins-log.css"
	}
}

window.onload = function(ev) {
	init()
}
