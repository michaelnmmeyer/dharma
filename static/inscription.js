let displays = ["logical", "physical", "full", "xml"]
let currentDisplay = "logical"

function displayButton(name) {
	return document.querySelector("#" + name + "-btn")
}

function switchDisplayTo(name) {
	for (let display of displays) {
		if (display == name) {
			displayButton(name).classList.add("active")
		} else {
			displayButton(name).classList.remove("active")
		}
	}
	for (let node of document.querySelectorAll("[data-display]")) {
		if (node.dataset.display == name) {
			node.classList.remove("hidden")
		} else {
			node.classList.add("hidden")
		}
	}
	currentDisplay = name
}

window.addEventListener("load", function () {
	for (let name of displays) {
		let button = displayButton(name)
		if (!button) {
			continue
		}
		button.addEventListener("click", function () {
			switchDisplayTo(name)
		})
	}
})
