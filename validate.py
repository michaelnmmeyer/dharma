# Jing manual: https://relaxng.org/jclark/jing.html

# Note that we use jing instead of lxml for validating RNG schemas because lxml
# apparently can't process our current schemas and goes into an infinite loop.
# This because of the embedded schematron stuff? or because we use XPath v. 2?
# I tried to remove the schematron stuff, it doesn't help.
# Update 2023/11/01: Now our schemas do parse with lxml (because of an update
# to lxml? not sure), but validation results are not the same as jing and seem
# wrong. Error messages produced by lxml are also really bad compared to those
# of jing, so using jing really is the only option.
#
# I checked jing's source code. It appears that it is not possible to get
# something else than line:col for locating errors, because errors are reported
# to this:
# https://docs.oracle.com/javase/1.5.0/docs/api/org/xml/sax/ErrorHandler.html

import os, sys, re, subprocess
from glob import glob
from dharma import config, texts, tree, parse_ins
from saxonche import PySaxonProcessor

def utf16_units_to_codepoints(s, n16):
	i16, i = 0, 0
	while i16 < n16:
		if ord(s[i]) > 0xffff:
			assert i16 + 1 < n16
			i16 += 1
		i16 += 1
		i += 1
	return i

# What should we use for representing error locations? Maybe just the patch the tree directly, since we're already doing that in python
# use validation levels: fatal (invalid xml), invalid (rng or sch error), warning (grapheme issues, maybe rng or sch advice)

class Schema:

	def __init__(self, name, prefix):
		self.name = name
		self.prefix = prefix
		self.saxon_proc = PySaxonProcessor(license=False)
		xslt_proc = self.saxon_proc.new_xslt30_processor()
		path = os.path.join(config.THIS_DIR, "schemas", self.name + ".sch")
		self.sch_script = xslt_proc.compile_stylesheet(stylesheet_file=path)

	def validate_rng(self, files):
		jar = os.path.join(config.THIS_DIR, "jars", "jing.jar")
		schema = os.path.join(config.THIS_DIR, "schemas", self.name + ".rng")
		cmd = ["java", "-jar", jar, schema] + sorted(files)
		print(*cmd, file=sys.stderr)
		ret = subprocess.run(cmd, encoding="UTF-8", stdout=subprocess.PIPE)
		errors = {file: set() for file in files}
		for line in ret.stdout.splitlines():
			path, line, column, err_type, err_msg = tuple(
				f.strip() for f in line.split(":", 4))
			errors[path].add((int(line), int(column), err_msg))
		new_errors = {}
		for path, errs in errors.items():
			# We don't use str.splitlines() because it counts U+2028 and
			# U+2029 as line separators, while jing doesn't (nor github,
			# oxygen and normal text editors).
			with open(path) as f:
				lines = re.split(r"\r|\n|\r\n", f.read())
			new_errs = set()
			for line, column, err_msg in errs:
				# jing counts columns in utf-16 code units, not in code points
				column = utf16_units_to_codepoints(lines[line - 1], column - 1) + 1
				new_errs.add((line, column, err_msg))
			new_errors[path] = new_errs
		return new_errors

	def validate_sch(self, files):
		# Can pass source_file=str or xdm_node=PyXdmNode
		# Get an xdm_node with: document = proc.parse_xml(xml_text="<doc>...</doc>")
		for file in files:
			ret = self.sch_script.transform_to_string(source_file=file)
			xml = tree.parse_string(ret)
			for node in xml.find("//successful-report"):
				loc = node["location"]
				loc = re.sub(r"/\*:([a-zA-Z]+)\[.+?\]\[([0-9]+)\]", r"/\1[\2]", loc)
				test = node["test"]
				msg = node.text()
				print(loc, test, msg)

SCHEMAS = [
	Schema("inscription", "DHARMA_INS"),
	Schema("diplomatic", "DHARMA_DiplEd"),
	Schema("critical", "DHARMA_CritEd"),
]

def schema_from_filename(file):
	base = os.path.basename(file)
	for schema in SCHEMAS:
		if base.startswith(schema.prefix):
			return schema

def validate_extra(file):
	schema = schema_from_filename(file)
	if not schema or schema.name != "inscription":
		return
	doc = parse_ins.process_file(file)
	errs = sorted(doc.tree.bad_nodes, key=lambda node: node.location)
	for node in errs:
		print(node, node.problems)

def validate(files):
	schemas = {}
	files = sorted(files)
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
		for text, errs in schema.validate_rng(texts).items():
			errors.setdefault(text, set()).update(errs)
	return {text: sorted(errs) for text, errs in errors.items()}

def repo(name):
	return validate(texts.iter_texts_in_repo(name))

if __name__ == "__main__":
	schema = Schema("inscription", "DHARMA_INS")
	schema.validate_sch(sys.argv[1:])
