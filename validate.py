#!/usr/bin/env python3

import os, sys, subprocess
from glob import glob

this_dir = os.path.dirname(os.path.abspath(__file__))

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
	files = sys.argv[1:]
	rc = 0
	for rng in ("tei-epidoc.rng", "DHARMA_Schema.rng"):
		ret = validate_texts(files)
		for path, errs in sorted(ret.items()):
			print("#", path)
			for err in errs:
				print("%s:%s: %s" % err)
		if ret:
			rc = 1
	sys.exit(rc)
