"""
This does the following:

* Drop the initial BOM, if any
* Remove spurious whitespace at the end of each line (this breaks markdown code
  that uses trailing spaces instead of <br>, but this convention is stupid
  anyway so we don't care).
* Use the same newline character throughout
* Drop empty lines at the beginning of the file and at its end
* Make sure the file ends with a newline character
* Normalize the text to NFC

Should also normalize whitespace and remove weird chars, at least:
* DerivedNormalizationProps.txt:Default_Ignorable_Code_Point
* PropList.txt:White_Space
"""

import io, sys, unicodedata

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
		line = line.replace("\N{CYRILLIC SMALL LETTER SCHWA}", "\N{LATIN SMALL LETTER SCHWA}")
		yield line + "\n"
		wrote = True

def complain(msg):
	print("%s: %s" % (os.path.basename(sys.argv[0]), msg), file=sys.stderr)

def die(msg):
	complain(msg)
	exit(1)

def normalize_filter(r, w):
	for line in cleanup_file(r):
		w.write(line)
		w.flush()

def normalize_string(s):
	inp = io.StringIO(s)
	out = io.StringIO()
	normalize_filter(inp, out)
	return out.getvalue()

def normalize_stdin():
	try:
		normalize_filter(sys.stdin, sys.stdout)
	except Exception as e:
		die(e)

def normalize_to_stdout(files):
	if len(files) > 1 or os.path.isdir(files[0]):
		complain("can only process a single file when writing to stdout")
		exit(1)
	try:
		with open(files[0]) as f:
			normalize_filter(f, sys.stdout)
	except Exception as e:
		die(e)

def iter_files(roots):
	for path in roots:
		if os.path.isdir(path):
			for root, dirs, files in os.walk(path):
				for file in files:
					name = os.path.join(root, file)
					yield name
		else:
			yield path

def normalize_single_in_place(name):
	with tempfile.NamedTemporaryFile(mode="w") as tmp:
		with open(name) as f:
			normalize_filter(f, tmp)
		shutil.copyfile(tmp.name, name)

def normalize_in_place(*files):
	err = False
	for path in iter_files(files):
		try:
			normalize_single_in_place(path)
		except UnicodeDecodeError:
			complain("%r: ignored (binary)" % path)
		except FileNotFoundError:
			complain("%r: ignored (not found)" % path)
			err = True
		except Exception as e:
			die(e)
	exit(err)


if __name__ == "__main__":
	import os, argparse, tempfile, shutil
	parser = argparse.ArgumentParser(description="""Normalize text files. Print the result
		on the standard output, unless the -i option is used, in which case input
		files are modified in-place.""")
	parser.add_argument("-i", "--in-place", help="edit files in-place", action="store_true")
	parser.add_argument("file", nargs="*")
	args = parser.parse_args()
	if args.in_place:
		if not args.file:
			die("cannot process stdin in-place")
		normalize_in_place(*args.file)
	elif args.file:
		normalize_to_stdout(args.file)
	else:
		normalize_stdin()
