#!/usr/bin/env python3

# XXX how does jing counts columns? UTF-16 units? bytes? code points? Same
# question for python's xml.sax library. Note that we use jing instead of lxml
# for validating RNG schemas because lxml apparently can't process our current
# schemas (because of the embedded schematron stuff? or because we use XPath v.
# 2? try to remove the schematron stuff and see how it goes)

# XXX possible to check the compatibility of several relaxng schemas? so that
# instead of validating all files against several schemas, we can just check if
# our own schema is compatible with TEI and epidoc.

# For schema validation stuff we could supplement to the existing schemas
# fragment of rng schemas that validate just partic. cases to check, so we can
# check stuff like parent/descendants/etc. without rewriting the whole schema.


"""
The following should be ignored when inferring the rng schema:

texts/DHARMA_CritEdJatiMula.xml
texts/DHARMA_INSIDENKKurungan.xml
texts/DHARMA_INSIDENKMunggut.xml
texts/DHARMA_INSIDENKTajiGunung.xml
texts/DHARMA_INSSII04.xml
texts/DHARMA_INSSII01.xml
texts/DHARMA_INSSII02.xml
texts/DHARMA_INSSII03.xml
"""

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

import os, sys, subprocess
from glob import glob
from dharma import config, texts
from dharma.tree import parse, Error

def schema_from_contents(file):
	tree = parse(file)
	ret = set()
	for node in tree:
		if node.type != "instruction":
			continue
		if node.target != "xml-model":
			continue
		schema = node.get("href")
		if not schema:
			continue
		_, ext = os.path.splitext(schema)
		if ext != ".rng":
			continue
		if not "erc-dharma" in schema:
			continue
		schema = os.path.basename(schema)
		ret.add(schema)
	assert len(ret) <= 1, "several schemas for %r" % file
	if ret:
		return ret.pop()

def schema_from_filename(file):
	base = os.path.basename(file)
	if base.startswith("DHARMA_DiplEd"):
		schema = "DHARMA_DiplEDSchema.rng"
	elif base.startswith("DHARMA_CritEd"):
		schema = "DHARMA_CritEdSchema.rng"
	elif base.startswith("DHARMA_INS"):
		schema = "DHARMA_Schema.rng"
	else:
		schema = None
	return schema

# To test the DHARMA schemas, we must first figure out (from the files
# themselves?) which schema we should use.
def schema_for_file(file):
	print("determining schema of %r" % file)
	one = schema_from_filename(file)
	#two = schema_from_contents(file) # XXX too long to compute
	two = None
	if one and two:
		assert one == two, "several schemas for file %r" % file
	return one or two

def validate_against(schema, files):
	jar = os.path.join(config.THIS_DIR, "validation/jing.jar")
	schema = os.path.join(config.THIS_DIR, "validation", schema)
	cmd = ["java", "-jar", jar, schema] + sorted(files)
	print(*cmd, file=sys.stderr)
	ret = subprocess.run(cmd, encoding="UTF-8", stdout=subprocess.PIPE)
	errors = {file: set() for file in files}
	for line in ret.stdout.splitlines():
		path, line, column, err_type, err_msg = tuple(
			f.strip() for f in line.split(":", 4))
		errors[path].add((int(line), int(column), err_msg))
	return errors

def validate(files):
	schemas = {}
	files = sorted(files)
	for file in files:
		try:
			schema = schema_for_file(file)
		except Error:
			schema = None # XXX what to report?
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
	validate_all()
