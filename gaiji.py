import os
from dharma import config

def gather_images():
	ret = {}
	path = os.path.join(config.STATIC_DIR, "gaiji")
	for file in os.listdir(path):
		name, ext = os.path.splitext(file)
		ext = ext.lower()
		if ext not in (".svg", ".jpg", ".png"):
			continue
		assert not name in ret, "duplicate gaiji image %r" % file
		url = "/gaiji/%s" % file
		ret[name] = url
	return ret

def iter_rows():
	path = os.path.join(config.THIS_DIR, "gaiji.tsv")
	field_names = None
	with open(path) as f:
		for line_no, line in enumerate(f, 1):
			fields = [f.strip() for f in line.split("\t")]
			if line_no == 1:
				assert len(fields) == 4, fields
				field_names = fields
				continue
			fields = dict(zip(field_names, fields))
			assert len(fields) == 4, fields
			yield line_no, fields

def default_rec(name):
	return {
		"name": name,
		"text": "(%s)" % name,
		"prefer_text": False,
		"img": None,
		"description": "no description available",
	}

def load():
	ret = {}
	imgs = gather_images()
	for line_no, row in iter_rows():
		assert row["names"], "the column 'names' should not be empty"
		names = set(row["names"].split())
		row["img"] = None
		for name in names:
			img = imgs.get(name)
			if not img:
				continue
			assert row["img"] is None, "duplicate images for symbol %r" % name
			row["img"] = img
			del imgs[name]
		row["prefer_text"] = row["prefer_text"] == "yes"
		if not row["description"]:
			row["description"] = "no description available"
		for name in names:
			assert not name in ret, "duplicate symbol %r" % name
			rec = row.copy()
			del rec["names"]
			rec["name"] = name
			if not rec["text"]:
				rec["text"] = "(%s)" % name
			ret[name] = rec
	for name, img in imgs.items():
		rec = default_rec(name)
		rec["img"] = img
		ret[name] = rec
	return ret

DATA = load()

def get(name):
	ret = DATA.get(name)
	if not ret:
		return default_rec(name)
	return ret
