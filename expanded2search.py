from dharma import tree

# Handlers are tested per order of appearance in this file, so the most
# specific ones should come first.
HANDLERS = []

def handler(path):
	def decorator(f):
		HANDLERS.append((tree.Node.match_func(path), f))
		return f
	return decorator

@handler("*")
def render_rest(self, node):
	pass

class SearchDocument:

	def __init__(self):
		pass

class SearchRenderer(tree.Serializer):

	def __init__(self, input):
		super().__init__()
		self.input = input
		self.document = SearchDocument()

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
	render = SearchRenderer(doc)
	doc = render()
	print(doc)
	return doc
