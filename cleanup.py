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

if __name__ == "__main__":
	for line in cleanup_file(sys.stdin):
		sys.stdout.write(line)
		sys.stdout.flush()
