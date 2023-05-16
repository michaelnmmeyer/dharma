#!/usr/bin/env python3

import os, re, sys
from bs4 import BeautifulSoup
from cleanup import cleanup_file

def complain(s):
	print(f"BUG: {s}", file=sys.stderr)

def iter_texts_in_repo(name):
	path = os.path.join("repos", name)
	for root, dirs, files in os.walk(path):
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
			if "template" in file.lower():
				continue
			yield os.path.join(root, file)

repos_to_ignore = {
	"digital-areal",
	"mdt-authorities",
	"project-documentation",
}

def iter_texts():
	unique = {}
	for repo in os.listdir("repos"):
		if repo in repos_to_ignore:
			continue
		for file in iter_texts_in_repo(repo):
			base = os.path.basename(file)
			unique.setdefault(base, []).append(file)
	for base, files in sorted(unique.items()):
		files.sort()
		if len(files) > 1:
			complain(f"several files bear the same name: {files}")
			# Refuse to process them
		else:
			yield files[0]

TEXTS_DIR = "texts"

def gather_texts():
	os.makedirs(TEXTS_DIR, exist_ok=True)
	for file in iter_texts():
		base = os.path.basename(file)
		out = os.path.join(TEXTS_DIR, base)
		with open(file) as r, open(out, "w") as w:
			for line in cleanup_file(r):
				w.write(line)

# Create a map xml->web page (for debugging)
def gather_web_pages():
	tbl = {os.path.basename(file): "" for file in iter_texts()}
	for root, dirs, files in os.walk("repos"):
		for file in files:
			name, ext = os.path.splitext(file)
			if ext != ".html":
				continue
			xml = f"{name}.xml"
			if not xml in tbl:
				continue
			html = os.path.join(root, file)
			url = "https://erc-dharma.github.io" + html[html.index("/"):]
			tbl[xml] = url
	for xml, html in sorted(tbl.items()):
		print(xml, html, sep="\t")

gather_web_pages()
