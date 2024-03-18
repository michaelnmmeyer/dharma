import os, sys, re, subprocess
from glob import glob
from dharma import config, texts, tree, parse_ins, unicode, relaxng
from saxonche import PySaxonProcessor

# What should we use for representing error locations? Maybe just the patch the
# tree directly, since we're already doing that in python. But then must be able
# to address text nodes, etc.

# Validation levels
OK = 0		# No problem
WARNING = 1	# Possible Unicode issues
ERROR = 2	# Schema error
FATAL = 3	# Invalid XML, cannot be processed at all

def splitlines(text):
	return re.findall(r"(.*)(?:\r\n|\r|\n)", text)

class Message:

	line = -1
	column = -1
	text = None
	assertion = None # schematron

	def __repr__(self):
		ret = f"{self.line}:{self.column}: {self.text}"
		if self.assertion:
			ret += f" {self.assertion}"
		return ret

class Result:

	def __init__(self):
		self.status = OK
		self.messages = []
		self.unicode = []

class Validator:

	def __init__(self, name, prefix):
		self.name = name
		self.prefix = prefix
		self.saxon_proc = PySaxonProcessor(license=False)
		xslt_proc = self.saxon_proc.new_xslt30_processor()
		path = config.path_of("schemas", self.name + ".sch")
		self.sch_script = xslt_proc.compile_stylesheet(stylesheet_file=path)
		path = config.path_of("schemas", self.name + ".rng")
		self.rng_schema = relaxng.Schema(path)

	def quick_check(self, file):
		try:
			tree.parse(file)
		except tree.Error:
			return FATAL
		if self.rng_schema(file):
			return ERROR
		if self.sch_error_nodes(file):
			return ERROR
		if self.uni_errors(file):
			return WARNING
		return OK

	def process(self, file):
		val = Result()
		try:
			xml = tree.parse(file)
		except tree.Error as e:
			val.status = FATAL
			m = Message()
			m.line = e.line
			m.column = e.column
			m.text = e.text
			val.messages.append(m)
			return val
		self.rng(file, val, xml)
		self.sch(file, val, xml)
		self.uni(file, val, xml)
		# XXX fix sorting of error messages, see https://dharman.in/texts/tfd-nusantara-philology/b2f464385320afc185560c9a42b8ed71873b3171/DHARMA_CritEdCalonArang
		val.messages.sort(key=lambda x: (x.line, x.column))
		return val

	def rng(self, file, val, xml):
		errs = self.rng_schema(file)
		if not errs:
			return
		val.status = ERROR
		for err in errs:
			m = Message()
			m.line = err.line
			m.column = err.column
			m.text = err.text
			val.messages.append(m)

	def sch_error_nodes(self, file):
		# PyXslt30Processor.transform_to_string(source_file=path) is
		# buggy. When the filename contains space characters, it
		# returns None. So we read the file manually and use
		# transform_to_string(xdm_node=doc) instead, which does work.
		with open(file) as f:
			text = f.read()
		if text.startswith("\N{BOM}"):
			text = text[1:]
		doc = self.saxon_proc.parse_xml(xml_text=text)
		ret = self.sch_script.transform_to_string(xdm_node=doc)
		assert ret is not None, file
		rep = tree.parse_string(ret)
		return rep.find("//successful-report")

	def sch(self, file, val, xml):
		errs = self.sch_error_nodes(file)
		if not errs:
			return
		val.status = ERROR
		for node in errs:
			loc = node["location"]
			loc = re.sub(r"/\*:([a-zA-Z]+)\[.+?\]\[([0-9]+)\]", r"/\1[\2]", loc)
			test = node["test"]
			msg = node.text()
			where = xml.first(loc).location
			m = Message()
			m.line, m.column, m.text, m.assertion = where.line, where.column, msg, test
			val.messages.append(m)

	def uni_errors(self, file):
		with open(file) as f:
			text = f.read()
		return unicode.validate(text)

	def uni(self, file, val, xml):
		ret = self.uni_errors(file)
		if not ret:
			return
		if val.status < WARNING:
			val.status = WARNING
		val.unicode = ret

VALIDATORS = [
	Validator("inscription", "DHARMA_INS"),
	Validator("diplomatic", "DHARMA_DiplEd"),
	Validator("critical", "DHARMA_CritEd"),
]

def schema_from_filename(file):
	base = os.path.basename(file)
	for schema in VALIDATORS:
		if base.startswith(schema.prefix):
			return schema

def status(path):
	validator = schema_from_filename(path)
	if not validator:
		return
	return validator.quick_check(path)

def file(path):
	validator = schema_from_filename(path)
	if not validator:
		return # XXX
	return validator.process(path)

def files(itor):
	schemas = {}
	files = sorted(itor)
	for file in files:
		schema = schema_from_filename(file)
		if not schema:
			continue
		schemas.setdefault(schema, set()).add(file)
	# We don't validate files against epidoc at this stage. If our schemas
	# are correct, our texts should also validate against epidoc. It's
	# something we must check internally, this doesn't concern the user.
	errors = {}
	for schema, texts in schemas.items():
		for text, errs in schema.rng(texts).items():
			errors.setdefault(text, set()).update(errs)
	return {text: sorted(errs) for text, errs in errors.items()}

if __name__ == "__main__":
	schema = Validator("inscription", "DHARMA_INS")
	for file in sys.argv[1:]:
		ret = schema.process(file)
		print(file, ret.status)
		for m in ret.messages:
			print(f"{file}:{m}")
