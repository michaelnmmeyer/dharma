#!/usr/bin/env python3

"""
This does the following:
* Drop the initial BOM, if any
* Remove spurious whitespace at the end of each line
  (might be problematic for markdown)
* Use the same newline character throughout
* Drop empty lines at the beginning of the file and at its end
* Make sure the file ends with a newline character
* Normalize the text to NFC

Should also normalize whitespace and remove weird chars, at least:
* DerivedNormalizationProps.txt:Default_Ignorable_Code_Point
* PropList.txt:White_Space
"""

import sys, unicodedata

first = True
empty = 0
wrote = False
for line in sys.stdin:
	line = line.rstrip()
	if first:
		first = False
		if line.startswith('\N{BOM}'):
			line = line[1:]
	if not line:
		empty += 1
		continue
	if wrote:
		for _ in range(empty):
			print()
	line = unicodedata.normalize("NFC", line)
	print(line)
	wrote = True
	empty = 0
