# https://www.w3.org/TR/1999/REC-xpath-19991116
# https://github.com/we-like-parsers/pegen
# https://we-like-parsers.github.io/pegen/

import inspect, fnmatch, argparse, io, os, sys, tokenize, traceback
from pegen.tokenizer import Tokenizer
from dharma import tree
from dharma.xpath_parser import *

def xpath_not(node, result):
	return not result

def xpath_glob(node, pattern):
	assert isinstance(pattern, str)
	return fnmatch.fnmatchcase(node.text(), pattern)

xpath_funcs = {
	"not": xpath_not,
	"glob": xpath_glob,
}

def children(node):
	for child in node:
		if isinstance(child, tree.Tag):
			yield child

def descendants(node):
	for child in node:
		if isinstance(child, tree.Tag):
			yield child
			yield from descendants(child)

def descendants_or_self(node):
	yield node
	yield from descendants(node)

def ancestors(node):
	while True:
		node = node.parent
		if not node:
			break
		yield node

def ancestors_or_self(node):
	yield node
	yield from ancestors(node)

xpath_globals = {f.__name__: f
	for funcs in (xpath_funcs.values(), (children, descendants,
		descendants_or_self, ancestors, ancestors_or_self))
		for f in funcs}

class Generator:

	def __init__(self):
		self.routines = []
		self.indents = []
		self.bufs = []
		self.routines_nr = 0
		self.env = xpath_globals.copy()
		self.table = {}

	def parse(self, expression):
		tokengen = tokenize.generate_tokens(io.StringIO(expression).readline)
		tokengen = (x for x in tokengen if x.type != tokenize.NEWLINE)
		tokenizer = Tokenizer(tokengen, verbose=False)
		parser = GeneratedParser(tokenizer, verbose=False)
		root = parser.start()
		if not root:
			err = parser.make_syntax_error("<xpath expression>")
			traceback.print_exception(err.__class__, err, None)
			raise err
		return root

	def start_routine(self):
		buf = []
		self.indents.append(0)
		self.bufs.append(buf)
		self.routines_nr += 1
		return f"xpath_expression_{self.routines_nr}"

	def end_routine(self):
		self.routines.append(self.bufs.pop())
		self.indents.pop()

	def compile(self, expr):
		f = self.table.get(expr)
		if f:
			return f
		tree = self.parse(expr)
		if os.getenv("DHARMA_DEBUG"):
			print(tree, file=sys.stderr)
		assert isinstance(tree, Path)
		main = f"xpath_expression_{self.routines_nr + 1}"
		self.generate(tree)
		buf = []
		for i, routine in enumerate(self.routines):
			for line in routine:
				buf.append(line)
			if i < len(self.routines) - 1:
				buf.append("\n")
		source = "".join(buf)
		code = compile(source, "<xpath expression>", "exec")
		exec(code, self.env)
		f = self.env[main]
		setattr(f, "source_code", source)
		self.table[expr] = f
		self.routines.clear()
		self.indents.clear()
		self.bufs.clear()
		return f

	def generate(self, expr):
		match expr:
			case Path():
				name = self.start_routine()
				self.generate_path(expr, name)
				self.end_routine()
				return f"(next({name}(node), None) is None)"
			case Step():
				self.generate_step(expr)
			case str():
				return expr
			case Op(val="or") | Op(val="and"):
				return f"bool({self.generate(expr.l)} {expr.val} {self.generate(expr.r)})"
			case Op():
				return f"({self.generate(expr.l)} {expr.val} {self.generate(expr.r)})"
			case Func():
				return self.generate_call(expr)
			case _:
				assert 0, "%r" % expr

	def append(self, line):
		self.bufs[-1].append(self.indents[-1] * "\t" + line + "\n")
		if line.startswith("def ") or line.startswith("if ") \
			or line.startswith("for "):
			self.indents[-1] += 1

	def generate_path(self, path, func_name):
		self.append(f"def {func_name}(node):")
		if path.absolute:
			self.append("node = node.tree")
		for step in path.steps:
			self.generate(step)
		self.append("yield node")

	def generate_step(self, step):
		match step.axis:
			case "self":
				pass
			case "child":
				self.append("for node in children(node):")
			case "descendant":
				self.append("for node in descendants(node):")
			case "descendant-or-self":
				self.append("for node in descendants_or_self(node):")
			case "parent":
				self.append("node = node.parent or node.tree")
				self.append("if node:")
			case "ancestor":
				self.append("for node in ancestors(node):")
			case "ancestor-or-self":
				self.append("for node in ancestors_or_self(node):")
			case _:
				assert 0, repr(step.axis)
		if step.name_test:
			self.append("if node.name == %r:" % step.name_test)
		for pred in step.predicates:
			self.append(f"if {self.generate(pred)}:")

	def generate_call(self, func):
		buf = []
		f = xpath_funcs.get(func.name)
		if not f:
			raise Exception(f"xpath function '{func.name}' not defined")
		# The following does not work if varargs are involved.
		arity = len(inspect.getfullargspec(f).args) - 1
		if arity != len(func.args):
			raise Exception(f"xpath function '{func.name}' takes {arity} arguments, but is called with {len(func.args)}")
		buf.append(f"{f.__name__}(node, ")
		for i, arg in enumerate(func.args):
			buf.append(self.generate(arg))
			if i < len(func.args) - 1:
				buf.append(", ")
		buf.append(")")
		return "".join(buf)

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("expression")
	parser.add_argument("file", nargs="*")
	args = parser.parse_args()
	f = Generator().compile(args.expression)
	if not args.file:
		sys.stdout.write(f.source_code)
		return
	for file in args.file:
		try:
			t = tree.parse(file)
		except tree.Error:
			continue
		for result in f(t):
			print(f"--- {file}")
			print(result.xml())

if __name__ == "__main__":
	main()
