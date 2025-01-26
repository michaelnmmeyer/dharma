# Stuff for enumerating texts (inscriptions, etc.) in a repository.

import os, unicodedata
from dharma import common, validate

valid_prefixes = {"DHARMA_INS", "DHARMA_DiplEd", "DHARMA_CritEd"}

class File:

	# Repo name ("tfa-pallava-epigraphy", etc.)
	repo = None

	# File path relative to the repository directory e.g.
	# "texts/xml/DHARMA_INSPallava00002.xml"
	path = None

	# Path of the corresponding HTML file generated with XSLT, relative to
	# the repo root, e.g.
	# "texts/htmloutput/DHARMA_INSPallava00002.html"
	html = None

	def __init__(self, repo, path):
		self.repo = repo
		self.path = path

	# Validation status. See the enum in validate.py.
	@property
	def status(self):
		ret = getattr(self, "_status", None)
		if ret is None:
			ret = validate.status(self)
			setattr(self, "_status", ret)
		return ret

	# File basename without the extension e.g. DHARMA_INSPallava00002
	@property
	def name(self):
		return os.path.splitext(os.path.basename(self.path))[0]

	# Value of st_mtime. We use this to figure out which files have been
	# updated after we do a pull. We do not rely on git both because this is
	# unnecessary and because at a later point we will want to be able to
	# track other sources than git repos, maybe with inotify or friends.
	@property
	def mtime(self):
		ret = getattr(self, "_mtime", None)
		if ret is None:
			ret = int(os.stat(self.full_path).st_mtime)
			setattr(self, "_mtime", ret)
		return ret

	# File contents, as a byte string
	@property
	def data(self):
		ret = getattr(self, "_data", None)
		if ret is None:
			with open(self.full_path, "rb") as f:
				ret = f.read()
			setattr(self, "_data", ret)
		return ret

	@property
	def text(self):
		return unicodedata.normalize("NFC", self.data.decode())

	# Git names of the people who modified this file, as a sorted set.
	# This is used in the debugging page so that people can filter by
	# their name.
	@property
	def owners(self):
		ret = getattr(self, "_owners", None)
		if ret is None:
			out = common.command("git",
				"-C", common.path_of("repos", self.repo),
				"log", "--follow", "--format=%aN", "--", self.path)
			ret = sorted(set(out.stdout.splitlines()))
			assert len(ret) > 0
			setattr(self, "_owners", ret)
		return ret

	# When the file was last modified according to git. A tuple
	# (commit_hash, commit_timestamp). This is only for display, for
	# convenience.
	@property
	def last_modified(self):
		ret = getattr(self, "_last_modified", None)
		if ret is None:
			out = common.command("git",
				"-C", common.path_of("repos", self.repo), 		"log", "-1", "--format=%H %at", "--", self.path)
			commit, date = out.stdout.strip().split()
			date = int(date)
			ret = (commit, date)
			setattr(self, "_last_modified", ret)
		return ret

	# Full absolute path of the file in the file system, e.g.
	# /home/michael/dharma/repos/tfa-pallava-epigraphy/texts/xml/DHARMA_INSPallava00002.xml"
	@property
	def full_path(self):
		return common.path_of("repos", self.repo, self.path)

def iter_texts_in_repo(repo):
	repo_path = common.path_of("repos", repo)
	for root, dirs, files in os.walk(repo_path):
		for file in files:
			_, ext = os.path.splitext(file)
			if ext.lower() != ".xml":
				continue
			if not any(file.startswith(p) for p in valid_prefixes):
				continue
			if "template" in file.lower():
				continue
			full_path = os.path.join(root, file)
			rel_path = os.path.relpath(full_path, repo_path)
			yield File(repo, rel_path)

def iter_texts():
	for repo in os.listdir(common.path_of("repos")):
		yield from iter_texts_in_repo(repo)

def save(repo, path):
	file = File(repo, path)
	db = common.db("texts")
	db.save_file(file)
	return file

# Find out the path of HTML files generated from each file, so that we can link
# to them in the website. The location of these files varies between repos, so
# we use brute force instead of hardcoding stuff.
def gather_web_pages(repo, recs):
	lookup = {file.name: file for file in recs}
	repo_path = common.path_of("repos", repo)
	for root, dirs, files in os.walk(repo_path):
		for file in files:
			name, ext = os.path.splitext(file)
			if ext != ".html":
				continue
			rec = lookup.get(name)
			if not rec:
				continue
			html = os.path.join(root, file)
			rec.html = os.path.relpath(html, repo_path)
