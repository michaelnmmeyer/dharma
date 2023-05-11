#!/usr/bin/env python3

import os, re
from bs4 import BeautifulSoup

def iter_texts():
	for root, dirs, files in os.walk("repos"):
		# There are generated files in
		# repos/tfc-nusantara-epigraphy/workflow-output/editedxml
		# They are produced with
		# repos/project-documentation/editorialStylesheets/tpl-editorialConvention.xsl

		# This does some basic formatting (space, quotation marks), but
		# doesn't change the structure of the document, so we can
		# ignore it and work on the originals. We'll add something do
		# this kind of formatting later on, for all documents, or maybe
		# just modify files directly.
		try:
			dirs.remove("workflow-output")
		except ValueError:
			pass
		for file in files:
			_, ext = os.path.splitext(file)
			if ext != ".xml":
				continue
			if not file.startswith("DHARMA_"):
				continue
			# Metadata
			if file.startswith("DHARMA_mdt"):
				continue
			yield os.path.join(root, file)

for file in iter_texts():
	print(file)
