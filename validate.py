# Jing manual: https://relaxng.org/jclark/jing.html

# Note that we use jing instead of lxml for validating RNG schemas because lxml
# apparently can't process our current schemas and goes into an infinite loop.
# This because of the embedded schematron stuff? or because we use XPath v. 2?
# I tried to remove the schematron stuff, it doesn't help.

# XXX possible to check the compatibility of several relaxng schemas? so that
# instead of validating all files against several schemas, we can just check if
# our own schema is compatible with TEI and epidoc.

# For schema validation stuff we could supplement to the existing schemas
# fragment of rng schemas that validate just partic. cases to check, so we can
# check stuff like parent/descendants/etc. without rewriting the whole schema.

# We have 4 schemas for 4 types of texts:
# * Inscriptions (INSSchema -> latest/Schema)
#   Is it actually only for inscriptions, or also more generic stuff?
# * Critical (CritEdSchema)
# * Diplomatic (DiplEdSchema)
# * BESTOW (in progress, so ignore for now)
# Share code or not? Are schemas different enough to warrant distinct parsers?
# Some files don't have an explicit schema for now:
# DHARMA_MS_Descr_Or3429.xml
# DHARMA_Sircar1965.xml

# For conversion and validation:
# https://teigarage.tei-c.org
#
# For editing an ODD:
# https://roma2.tei-c.org/
#
# For converting ODD XML->RNG:
# It's faster to do it online than locally because java takes forever to start.
# * curl -F fileToConvert=@DHARMA_INSSchema_v01.xml https://teigarage.tei-c.org/ege-webservice/Conversions/ODD%3Atext%3Axml/ODDC%3Atext%3Axml/relaxng%3Aapplication%3Axml-relaxng
# * ~/Programs/TEI/Stylesheets/bin/teitorelaxng --oxygenlib=~/.oxygen/lib --localsource=/home/michael/Programs/TEI/TEI/P5/Source/guidelines-en.xml  ~/Downloads/DHARMA_BESTOW_v01.xml ~/Downloads/foo.rng
#
# For validating TEI:
# * (buggy) curl -F fileToConvert=@DHARMA_INSSchema_v01.xml https://teigarage.tei-c.org/ege-webservice/Validation/TEI%3Atext%3Axml
# * java -jar ./project-documentation/schema/validationTools/jing.jar http://www.stoa.org/epidoc/schema/latest/tei-epidoc.rng $f
# * java -jar ./project-documentation/schema/validationTools/jing.jar https://raw.githubusercontent.com/erc-dharma/project-documentation/master/schema/latest/DHARMA_Schema.rng $f

import os, sys, re, subprocess
from glob import glob
from dharma import config, texts, tree, parse_ins

def schema_from_filename(file):
	base = os.path.basename(file)
	if base.startswith("DHARMA_DiplEd"):
		schema = "diplomatic"
	elif base.startswith("DHARMA_CritEd"):
		schema = "critical"
	elif base.startswith("DHARMA_INS"):
		schema = "inscription"
	else:
		schema = None
	return schema

def utf16_units_to_codepoints(s, n16):
	i16, i = 0, 0
	while i16 < n16:
		if ord(s[i]) > 0xffff:
			assert i16 + 1 < n16
			i16 += 1
		i16 += 1
		i += 1
	return i

def validate_against(schema, files):
	jar = os.path.join(config.THIS_DIR, "jars", "jing.jar")
	schema = os.path.join(config.THIS_DIR, "schemas", schema + ".rng")
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

def validate_extra(file):
	if schema_from_filename(file) != "inscription":
		return
	doc = parse_ins.process_file(file)
	errs = sorted(doc.tree.bad_nodes, key=lambda node: node.location)
	for node in errs:
		print(node, node.problems)

def validate(files):
	schemas = {}
	files = sorted(files)
	for file in files:
		try:
			schema = schema_from_filename(file)
		except tree.Error:
			pass # will deal with this later on
		if schema:
			schemas.setdefault(schema, set()).add(file)
	# We don't validate files against epidoc at this stage. If our schemas
	# are correct, our texts should also validate against epidoc. It's
	# something we must check internally, this doesn't concern the user.
	errors = {}
	for schema, texts in schemas.items():
		for text, errs in validate_against(schema, texts).items():
			errors.setdefault(text, set()).update(errs)
	return {text: sorted(errs) for text, errs in errors.items()}

def validate_repo(name):
	return validate(texts.iter_texts_in_repo(name))

def validate_all():
	files = glob(os.path.join(config.THIS_DIR, "texts", "*.xml"))
	errors = validate(files)
	for path, errs in sorted(errors.items()):
		path, _ = os.path.splitext(path)
		with open(path + ".err", "w") as f:
			for err in errs:
				print("%s:%s:%s" % err, file=f)

if __name__ == "__main__":
	for file in sys.argv[1:]:
		print(file)
		validate_extra(file)
