import os
from dharma import config

def iter_rows():
	path = config.path_of("repos/project-documentation/gaiji/DHARMA_gaiji.tsv")
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
			yield line_no, fields

def load_data():
	ret = {}
	for line_no, row in iter_rows():
		assert row["names"], "the column 'names' should not be empty"
		names = set(row["names"].split())
		if not row["description"]:
			row["description"] = "no description available"
		for name in names:
			assert not name in ret, "duplicate symbol %r" % name
			rec = row.copy()
			del rec["names"]
			rec["name"] = name
			if not rec["text"]:
				rec["text"] = None
			ret[name] = rec
	return ret

def get(name):
	db = config.db("texts")
	text, description = db.execute("""select text, description from gaiji
		where name = ?""", (name,)).fetchone() or (None, None)
	ret = {
		"name": name,
		"text": text,
		"description": description or "no description available",
	}
	return ret

def make_db():
	db = config.db("texts")
	data = load_data()
	db.execute("delete from gaiji")
	for _, row in sorted(data.items()):
		db.execute("insert into gaiji(name, text, description) values(?, ?, ?)",
			(row["name"], row["text"], row["description"]))

if __name__ == "__main__":
	ret = load_data()
	for k, v in ret.items():
		print(k, v, sep="\t")
