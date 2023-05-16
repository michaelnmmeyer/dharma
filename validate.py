#!/usr/bin/env python3

import os, sys, subprocess
from glob import glob

# For EpiDoc.
# To test the DHARMA schemas, we must first figure out (from the files
# themselves?) which schema we should use.
def validate_texts(files):
	ret = subprocess.run(["java", "-jar", "validation/jing.jar",
		"validation/tei-epidoc.rng"] + files,
		encoding="UTF-8", stdout=subprocess.PIPE)
	errors = {}
	for line in ret.stdout.splitlines():
		path, line, column, err_type, err_msg = tuple(
			f.strip() for f in line.split(":", 4))
		name = os.path.basename(path)
		errors.setdefault(name, []).append((line, column, err_msg))
	return errors

files = sys.argv[1:]
ret = validate_texts(files)
for name, errs in sorted(ret.items()):
	print(">>>", name)
	for err in errs:
		print("%s:%s: %s" % err)
