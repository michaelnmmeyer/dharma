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
		while True:
			self.cursor.next()
			match_start, match_len = self.cursor.match()
			if match_start < 0:
				self.start = -2
				self.length = 0
				return False
			start, length = self.transformer.translate(match_start, match_len)
			if start >= 0:
				break
		self.start, self.length = start, length
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

	def try_next_chars(self):
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
		chars = chunk[self.chunk_offset].casefold()
		self.chunk_offset += 1
		return chars

	def next_chars(self):
		ret = self.try_next_chars()
		if not ret:
			raise Exception
		return ret

	def translate(self, start, length):
		# süße > süsse
		# search "se": süs[se] ; arrondir en-dessous sü[sse] (2, 4)
		# search "üs": s[üs]se ; arrondir au-dessus  s[üss]e (1, 3)
		dstart = -1
		dlength = 0
		assert start >= 0 and length > 0
		if self.search_offset > start:
			if self.search_offset >= start + length:
				# We are in this situation if there are more
				# than one match in a single display unit. For
				# instance, if the original text is "süße", the
				# search text is "süsse", and the query is "s",
				# there will be two matches for the single
				# display unit "ß". In this case, we will
				# highlight "ß" a single time, so we ignore the
				# second match.
				return -1, 0
			start = self.search_offset
		assert self.search_offset <= start
		while self.search_offset < start:
			cs = self.next_chars()
			if self.search_offset + len(cs) > start:
				dstart = self.display_offset
				self.display_offset += 1
				self.search_offset += len(cs)
				if self.search_offset >= start + length:
					dlength = self.display_offset - dstart
					return dstart, dlength
			else:
				self.display_offset += 1
				self.search_offset += len(cs)
		if dstart < 0:
			dstart = self.display_offset
		assert self.search_offset >= start
		while self.search_offset < start + length:
			cs = self.next_chars()
			if self.search_offset + len(cs) > start + length:
				self.display_offset += 1
				dlength = self.display_offset - dstart
				self.search_offset += len(cs)
				return dstart, dlength
			self.display_offset += 1
			self.search_offset += len(cs)
		dlength = self.display_offset - dstart
		return dstart, dlength

if __name__ == "__main__":
	substring = Substring("se", "süsse")
	t = tree.Tree()
	t.append("süße")
	cursor = Tree(t, substring)
	while cursor.next():
		start, length = cursor.match()
		print(start, start + length)
