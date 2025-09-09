import unicodedata

from dharma import tree

class Cursor:

	def __init__(self):
		self.offset = 0

	def next(self):
		raise NotImplementedError

	def match(self):
		raise NotImplementedError

	def seek(self, offset):
		if self.offset < offset:
			self.offset = offset

class Substring(Cursor):

	def __init__(self, needle: str, source: str):
		assert len(needle) > 0
		self.needle = needle
		self.source = source
		self.offset = -len(self.needle)

	def next(self):
		if self.offset >= len(self.source):
			return False
		self.offset += len(self.needle)
		start = self.source.find(self.needle, self.offset)
		if start < 0:
			self.offset = len(self.source)
			return False
		self.offset = start
		return True

	def match(self):
		assert self.offset >= 0
		if self.offset >= len(self.source):
			return (-1, 0)
		return self.offset, len(self.needle)

class Tree(Cursor):

	def __init__(self, root: tree.Branch, cursor: Cursor):
		self.transformer = Tokenizer(*root.strings())
		self.start = -1
		self.length = 0
		self.cursor = cursor

	def next(self):
		if self.start == -2:
			return False
		self.cursor.next()
		match_start, match_len = self.cursor.match()
		if match_start < 0:
			self.start = -2
			self.length = 0
			return False
		self.transformer.seek(match_start)
		assert self.transformer.search_offset == match_start
		self.start = self.transformer.display_offset
		self.transformer.seek(match_start + match_len)
		assert self.transformer.search_offset == match_start + match_len
		self.length = self.transformer.display_offset - self.start
		return True

	def match(self):
		return self.start, self.length

class Tokenizer(Cursor):

	def __init__(self, *chunks):
		self.chunks = chunks
		self.chunk = 0
		self.chunk_offset = 0
		self.search_offset = 0
		self.display_offset = 0

	def next(self):
		assert self.chunk <= len(self.chunks)
		if self.chunk >= len(self.chunks):
			return ""
		chunk = self.chunks[self.chunk]
		assert self.chunk_offset <= len(chunk)
		if self.chunk_offset >= len(chunk):
			self.chunk += 1
			self.chunk_offset = 0
			if self.chunk >= len(self.chunks):
				return ""
			chunk = self.chunks[self.chunk]
		cs = chunk[self.chunk_offset].casefold()
		self.chunk_offset += 1
		self.display_offset += 1
		self.search_offset += len(cs)
		return cs

	def seek(self, offset):
		assert self.search_offset <= offset
		while self.search_offset < offset:
			self.next()
		assert self.search_offset == offset

	def transform(self):
		buf = []
		while (cs := self.next()):
			buf.append(cs)
		return "".join(buf)

if __name__ == "__main__":
	substring = Substring("ss", "süsse")
	t = tree.Tree()
	t.append("süße")
	cursor = Tree(t, substring)
	while cursor.next():
		print(*cursor.match())
