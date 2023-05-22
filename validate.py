#!/usr/bin/env python3

import os, sys, subprocess
from glob import glob
from dharma.tree import parse

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
	files = sys.argv[1:]
	ret = validate_texts(files)
	for path, errs in sorted(ret.items()):
		path, _ = os.path.splitext(path)
		with open(path + ".err", "w") as f:
			for err in errs:
				print("%s:%s: %s" % err, file=f)

if __name__ == "__main__":
	schema_from_contents(sys.argv[1])
