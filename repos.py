from dharma import config, texts

def iter_repos():
	f = texts.save("project-documentation", "DHARMA_repositories.tsv")
	for line_no, line in enumerate(f.data.decode().splitlines(), 1):
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

def make_db():
	db = config.db("texts")
	for _, rec in sorted(load_data().items()):
		db.execute("""
			insert into repos(repo, textual, title)
				values(:name, :textual, :title)
			on conflict do update
			set textual = excluded.textual, title = excluded.title""", rec)

if __name__ == "__main__":
	@config.transaction("texts")
	def main():
		make_db()
	main()
