#!/usr/bin/env python3

"""
This does the following:

* Drop the initial BOM, if any
* Remove spurious whitespace at the end of each line (this breaks markdown code
  that uses trailing spaces instead of <br/>, but this convention is stupid
  anyway so we don't care).
* Use the same newline character throughout
* Drop empty lines at the beginning of the file and at its end
* Make sure the file ends with a newline character
* Normalize the text to NFC

Should also normalize whitespace and remove weird chars, at least:
* DerivedNormalizationProps.txt:Default_Ignorable_Code_Point
* PropList.txt:White_Space
"""

import sys, unicodedata

def cleanup_file(f):
	first = True
	empty = 0
	wrote = False
	for line in f:
		line = line.rstrip()
		if first:
			first = False
			if line.startswith('\N{BOM}'):
				line = line[1:]
		if not line:
			empty += 1
			continue
		if wrote:
			while empty > 0:
				yield "\n"
				empty -= 1
		line = unicodedata.normalize("NFC", line)
		yield line + "\n"
		wrote = True
		empty = 0

OK = 0
BINARY = 1
FAIL = 2

def complain(msg):
	print("%s: %s" % (os.path.basename(sys.argv[0]), msg), file=sys.stderr)

def normalize_filter(r, w):
	try:
		for line in cleanup_file(r):
			w.write(line)
			w.flush()
		return OK
	except UnicodeDecodeError:
		return BINARY
	except Exception as e:
		complain("%s" % e)
		return FAIL

if __name__ == "__main__":
	import os, argparse, tempfile, shutil
	this_dir = os.path.dirname(os.path.abspath(__file__))
	parser = argparse.ArgumentParser(description="""Normalize text files. Print the result
		on the standard output, unless the -i option is used, in which case input
		files are modified in-place.""")
	parser.add_argument("-i", "--in-place", help="edit files in-place", action="store_true")
	parser.add_argument("file", nargs="*")
	args = parser.parse_args()
	failed = False
	if args.in_place and args.file:
		for name in args.file:
			with tempfile.NamedTemporaryFile(mode="w", dir=this_dir, delete=False) as tmp:
				try:
					with open(name) as f:
						ret = normalize_filter(f, tmp)
				except FileNotFoundError:
					complain("'%s': not found" % name)
					ret = FAIL
				if ret == OK:
					shutil.move(tmp.name, name)
				else:
					os.remove(tmp.name)
					if ret == FAIL:
						failed = True
	elif args.file:
		for name in args.file:
			try:
				with open(name) as f:
					if normalize_filter(f, sys.stdout) != OK:
						failed = True
			except FileNotFoundError:
				complain("'%s': not found" % name)
				failed = True

	else:
		if normalize_filter(sys.stdin, sys.stdout) != OK:
			failed = True
	sys.exit(not failed)
