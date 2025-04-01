from dharma import tree

HANDLERS = []

def handler(path):
	def decorator(f):
		HANDLERS.append((tree.Node.match_func(path), f))
		return f
	return decorator

@handler("document")
def render_document(self, node):
	self.heading_level += 1
	self.push(tree.Tag("div", id="inscription-display"))
	self.dispatch_children(node)
	self.heading_level -= 1
	if self.notes:
		self.push(tree.Tag("div", class_="notes"))
		render_head(self, "Notes")
		self.push(tree.Tag("ol"))
		for n, note in enumerate(self.notes, 1):
			self.push(tree.Tag("li", class_="note", id=f"note-{n}"))
			self.push(tree.Tag("a", class_="note-ref", href=f"#note-ref-{n}"))
			self.append(str(n))
			self.join()
			self.dispatch_children(note)
			self.join()
		self.join() # ol
		self.join() # div
	self.join()
	self.document.body = self.top

@handler("list")
def render_list(self, node):
	match node["type"]:
		case "plain":
			self.push(tree.Tag("ul", class_="list list-plain"))
		case "bulleted":
			self.push(tree.Tag("ul", class_="list"))
		case "numbered":
			self.push(tree.Tag("ol", class_="list"))
	for item in node.find("item"):
		self.push(tree.Tag("li"))
		self.dispatch_children(item)
		self.join()
	self.join()

@handler("summary")
@handler("hand")
@handler("editor")
def TODO(self, node):
	#self.dispatch_children(node)
	pass

edition_tabs = tree.parse_string("""
<ul class="ed-tabs">
	<li id="logical-btn" class="active"><a href="#">Logical</a></li>
	<li id="physical-btn"><a href="#">Physical</a></li>
	<li id="full-btn"><a href="#">Full</a></li>
</ul>""")

@handler("edition")
@handler("apparatus")
@handler("translation")
@handler("commentary")
@handler("bibliography")
def render_section(self, node):
	self.push("div", class_=node.name)
	self.dispatch_children(node)
	self.join()

@handler("logical")
@handler("physical")
@handler("full")
def render_edition_display(self, node):
	self.push("div", class_=node.name, id=node.name, data_display=node.name)
	if node.name != "logical":
		self.top["class"] += " hidden"
	self.dispatch_children(node)
	self.join()

@handler("note")
def handle_note(self, node):
	self.notes.append(node)
	n = len(self.notes)
	self.push(tree.Tag("a", class_="nav-link", href=f"#note-{n}", id="note-ref-{n}"))
	self.append(str(n))
	self.join()

@handler("title")
def render_title(self, node):
	self.push(tree.Tree())
	self.dispatch_children(node)
	self.document.title = self.pop()

@handler("dlist")
def render_dlist(self, node):
	self.push(tree.Tag("dl"))
	for child in node.find("*"):
		match child.name:
			case "key":
				self.push(tree.Tag("dt"))
			case "value":
				self.push(tree.Tag("dd"))
			case _:
				assert 0
		self.dispatch_children(child)
		self.join()
	self.join()

@handler("div")
def render_div(self, node):
	self.heading_level += 1
	self.dispatch_children(node)
	self.heading_level -= 1

@handler("edition/stuck-child::head")
def render_edition_head(self, node):
	self.push(tree.Tag(f"h{self.heading_level}"))
	self.dispatch_children(node)
	self.join()
	self.extend(edition_tabs)

@handler("head")
def render_head(self, node):
	self.push(tree.Tag(f"h{self.heading_level}"))
	self.dispatch_children(node)
	self.join()

@handler("npage")
@handler("nline")
@handler("ncell")
def render_milestone(self, node):
	match node.name:
		case "npage":
			class_ = "pagelike"
		case "nline":
			class_ = "lb"
		case "ncell":
			class_ = "gridlike"
	self.push(tree.Tag("span", class_=class_))
	self.dispatch_children(node)
	self.join()

@handler("*")
def render_tag(self, node):
	assert isinstance(node, tree.Tag)
	match node.name:
		case "para":
			self.push(tree.Tag("p"))
			for child in node:
				self.dispatch(child)
			self.join()
		case "span" | "a":
			self.append(node)
		case _:
			raise Exception(f"unknown: {node.name}")

@handler("note")
def render_note_ref(self, node):
	self.notes.append(node)
	n = len(self.notes)
	self.push(tree.Tag("sup"))
	self.push(tree.Tag("a", class_="nav-link", href=f"#note-{n}", id=f"note-ref-{n}"))
	self.append(str(n))
	self.join()
	self.join()

class HTMLDocument:

	def __init__(self):
		self.title = None
		self.body = None

class HTMLRenderer(tree.Serializer):

	def __init__(self, input):
		super().__init__()
		self.input = input
		self.notes = []
		self.heading_level = 1
		self.document = HTMLDocument()

	def __call__(self):
		self.clear()
		self.dispatch(self.input.root)
		return self.document

	def dispatch(self, node):
		match node:
			case tree.Comment() | tree.Instruction():
				return
			case tree.String() | str():
				self.append(node)
				return
			case tree.Tag() | tree.Tree():
				pass
			case _:
				raise Exception(f"unknown {node}")
		for matcher, f in HANDLERS:
			if matcher(node):
				break
		else:
			raise Exception
		f(self, node)

	def dispatch_children(self, node):
		for child in node:
			self.dispatch(child)

# We have an XML tree instead of a Document object as input because 1) we will
# need to process an XML tree for highlighting; and 2) because it is more
# convenient to use xpath.
def process(doc):
	render = HTMLRenderer(doc)
	doc = render()
	print(doc.body.html())
