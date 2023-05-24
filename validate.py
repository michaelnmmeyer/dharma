#!/usr/bin/env python3

# XXX too slow to call jing for each file! perform just one call for each
# distinct schema and pass several files


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

import os, sys, subprocess
from glob import glob
from dharma.tree import parse, Error

sys.stdout.reconfigure(line_buffering=True)

this_dir = os.path.dirname(os.path.abspath(__file__))

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

def schema_for_file(file):
	one = schema_from_filename(file)
	two = schema_from_contents(file)
	if one and two:
		assert one == two, "several schemas for file %r" % file
	return one or two

# For EpiDoc.
# To test the DHARMA schemas, we must first figure out (from the files
# themselves?) which schema we should use.
def validate_texts(files, rng="tei-epidoc.rng"):
	jar = os.path.join(this_dir, "validation/jing.jar")
	rng = os.path.join(this_dir, "validation", rng)
	ret = subprocess.run(["java", "-jar", jar, rng] + files,
		encoding="UTF-8", stdout=subprocess.PIPE)
	errors = {}
	for line in ret.stdout.splitlines():
		path, line, column, err_type, err_msg = tuple(
			f.strip() for f in line.split(":", 4))
		errors.setdefault(path, []).append((line, column, err_msg))
	return errors

def validate_all():
	texts = []
	path = os.path.join(this_dir, "texts")
	for root, dirs, files in os.walk(path):
		for file in files:
			_, ext = os.path.splitext(file)
			if ext != ".xml":
				continue
			text = os.path.join(root, file)
			try:
				schema = schema_for_file(text)
			except Error:
				schema = None
			texts.append((text, schema))
	errs = {}
	for (text, schema) in texts:
		print(text)
		e = validate_texts([text]).get(text, [])
		if schema:
			e += validate_texts([text], schema).get(text, [])
		if e:
			errs[text] = e
	for path, errs in sorted(errs.items()):
		path, _ = os.path.splitext(path)
		with open(path + ".err", "w") as f:
			for err in errs:
				print("%s:%s: %s" % err, file=f)

if __name__ == "__main__":
	validate_all()
