import os
from dharma import config

def iter_rows():
	path = os.path.join(config.THIS_DIR, "gaiji.tsv")
	field_names = None
	with open(path) as f:
		for line_no, line in enumerate(f, 1):
			fields = [f.strip() for f in line.split("\t")]
			if line_no == 1:
				assert len(fields) == 3, fields
				field_names = fields
				continue
			fields = dict(zip(field_names, fields))
			assert len(fields) == 3, fields
			names = fields["type"]
			assert names, "the column 'type' should not be empty"
			for name in names.split():
				row = fields.copy()
				row["type"] = name
				yield line_no, row

def load():
	ret = {}
	for line_no, row in iter_rows():
		assert not row["type"] in ret, "duplicate symbol %r" % row["type"]
		if not row["unicode"]:
			row["unicode"] = "(%s)" % row["type"]
		if not row["description"]:
			row["description"] = "no description available"
		ret[row["type"]] = row
	return ret

DATA = load()

def get(name):
	return DATA.get(name) or {"type": name, "unicode": "(%s)" % name, "description": "no description available"}
