import os, re, sys, logging
from dharma.cleanup import cleanup_file
from dharma import config

valid_prefixes = {"DHARMA_INS", "DHARMA_DiplEd", "DHARMA_CritEd"}

class File:

	# Repo name ("tfa-pallava-epigraphy", etc.)
	repo = None

	# File path, relative to the repository directory e.g.
	# "texts/xml/DHARMA_INSPallava00002.xml"
	path = None

	# Value of st_mtime. We use this to figure out which files have been
	# updated after we do a pull. We do not rely on git both because it is
	# unnecessary and because at a later point we will want to track local
	# dirs with inotify or friends.
	mtime = 0

	# Path of the corresponding HTML file generated with XSLT, relative to
	# the repo root, e.g.
	# "texts/htmloutput/DHARMA_INSPallava00002.html"
	html = None

	# Validation status. See the enum in validate.py.
	status = None

	_data = None

	# File basename without the extension e.g. DHARMA_INSPallava00002
	@property
	def name(self):
		return os.path.splitext(os.path.basename(self.path))[0]

	# File contents, as a byte string
	@property
	def data(self):
		if self._data is None:
			with open(self.full_path, "rb") as f:
				self._data = f.read()
		return self._data

	# Git names of the people who modified this file, as a sorted set.
	# This is used in the debugging page so that people can filter by
	# their name.
	@property
	def owners(self):
		return owners_of(self.full_path)

	# When the file was last modified according to git. A tuple
	# (commit_hash, commit_timestamp). This is only for display, for
	# convenience.
	@property
	def last_modified(self):
		return last_mod_of(self.full_path)

	# Full absolute path of the file in the file system, e.g.
	# /home/michael/dharma/repos/tfa-pallava-epigraphy/texts/xml/DHARMA_INSPallava00002.xml"
	@property
	def full_path(self):
		return os.path.join(config.REPOS_DIR, self.repo, self.path)

def iter_texts_in_repo(name):
	path = os.path.join(config.REPOS_DIR, name)
	for root, dirs, files in os.walk(path):
		# There are generated files in
		# repos/tfc-nusantara-epigraphy/workflow-output/editedxml
		# They are produced with
		# repos/project-documentation/editorialStylesheets/tpl-editorialConvention.xsl
		# This does some basic formatting (space, quotation marks), but
		# doesn't change the structure of the document, so we
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
			if not any(file.startswith(p) for p in valid_prefixes):
				continue
			if "template" in file.lower():
				continue
			yield os.path.join(root, file)

def iter_texts():
	unique = {}
	for repo in os.listdir(config.REPOS_DIR):
		for file in iter_texts_in_repo(repo):
			base = os.path.basename(file)
			unique.setdefault(base, []).append(file)
	for base, files in sorted(unique.items()):
		files.sort()
		if len(files) > 1:
			logging.error(f"several files bear the same name: {files}")
			# Refuse to process them
		else:
			yield files[0]

def owners_of(path):
	from dharma import people
	path = os.path.relpath(path, config.REPOS_DIR)
	slash = path.index("/")
	repo, relpath = path[:slash], path[slash + 1:]
	ret = config.command("git", "-C", os.path.join(config.REPOS_DIR, repo), "log", "--follow", "--format=%aN", "--", relpath)
	authors = set(ret.stdout.splitlines())
	return sorted(authors)

def last_mod_of(path):
	path = os.path.relpath(path, config.REPOS_DIR)
	slash = path.index("/")
	repo, relpath = path[:slash], path[slash + 1:]
	ret = config.command("git", "-C", os.path.join(config.REPOS_DIR, repo), "log", "-1", "--format=%H %at", "--", relpath)
	commit, date = ret.stdout.strip().split()
	return commit, int(date)

# Create a map xml->web page (for debugging)
def gather_web_pages(recs):
	tbl = {file.name: file for file in recs}
	for root, dirs, files in os.walk(config.REPOS_DIR): # XXX only the repo dir!
		for file in files:
			name, ext = os.path.splitext(file)
			if ext != ".html":
				continue
			rec = tbl.get(name)
			if not rec:
				continue
			html = os.path.join(root, file)
			rec.html = os.path.relpath(html, os.path.join(config.REPOS_DIR, rec.repo))
