from dharma import config

def iter_repos():
	with open("repos.tsv") as f:
		for line_no, line in enumerate(f, 1):
			fields = [field.strip() for field in line.split("\t")]
			if line_no == 1:
				assert len(fields) == 3
				field_names = fields
			else:
				row = dict(zip(field_names, fields))
				assert len(row) == len(field_names)
				assert row["textual"] in ("true", "false")
				row["textual"] = row["textual"] == "true"
				yield row

def load_data():
	repos = {}
	for row in iter_repos():
		assert not row["name"] in repos, row
		repos[row["name"]] = row
	return repos

@config.transaction("texts")
def make_db():
	db = config.db("texts")
	db.execute("begin")
	for _, rec in sorted(load_data().items()):
		db.execute("""
			insert into repos(repo, textual, title)
				values(:name, :textual, :title)
			on conflict do update
			set textual = excluded.textual, title = excluded.title""", rec)
	db.execute("commit")

if __name__ == "__main__":
	make_db()
