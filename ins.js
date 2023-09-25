function changeDisplay(stylesheet) {
	link = document.querySelector("#ins-display")
	if (link["ref"] == "") {
		link["href"] = stylesheet
	} else {
		link["href"] = ""
	}
}
function init() {
	document.querySelector("#phys-btn").onclick = function() {
		changeDisplay("ins-phys.css")
	}
}

window.onload = function(ev) {
	init()
}
