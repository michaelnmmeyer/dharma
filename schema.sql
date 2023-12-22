begin;

create table if not exists metadata(
	key text primary key,
	value blob
);
insert or ignore into metadata values('last_updated', 0);

create table if not exists commits(
	repo text primary key,
	commit_hash text check(length(commit_hash) = 2 * 20),
	commit_date integer
);

-- We store raw xml files in the db. The point is to make it possible to use
-- the main db read-only, without having to clone repos somewhere. We want
-- to store both texts and other xml files we need to render them (prosody,
-- members).
--
-- The repo name is needed only in the commits table and in the files table.
-- We reproduce it in other tables only to be able to easily delete everything
-- related to a repo when updating the db.
create table if not exists files(
	name text unique,
	repo text,
	path text,
	mtime timestamp,
	data text,
	primary key(name, repo),
	foreign key(repo) references commits(repo)
	-- The file is at https://github.com/erc-dharma/$repo/blob/master/$path
);

create table if not exists texts(
	name text primary key,
	repo text,
	html_path text check(html_path is null or length(html_path) > 1),
	code_hash text check(length(code_hash) = 2 * 20),
	-- See the enum in change.py
	status integer check(status >= 0 and status <= 3),
	when_validated timestamp,
	foreign key(name, repo) references files(name, repo)
	-- The HTML display is at https://erc-dharma.github.io/$repo/$html_path
);

create table if not exists owners(
	name text,
	git_name text,
	primary key(name, git_name),
	foreign key(name) references files(name)
);
create index if not exists owners_index on owners(git_name);

create table if not exists people_main(
	name json check(
		json_array_length(name) between 1 and 2
		and json_type(name -> 0) = 'text'
		and json_array_length(name) = 1 or json_type(name -> 1) = 'text'),
	print_name text as (iif(json_array_length(name) = 1,
		name ->> 0,
		printf('%s %s', name ->> 0, name ->> 1))),
	inverted_name text as (iif(json_array_length(name) = 1,
		name ->> 0,
		printf('%s, %s', name ->> 1, name ->> 0))),
	-- all the following can be null
	dh_id text unique check(dh_id is null or length(dh_id) = 4),
	idhal text unique,
	idref text unique,
	orcid text unique,
	viaf text unique,
	wikidata text unique
);

-- This is filled with git_names.csv. To dump a list of all contributors:
-- for repo in repos/*; do test -d $repo && git -C $repo log --format=%aN; done | sort -u
create table if not exists people_github(
	git_name text primary key not null,
	-- Might be null, not all people on github have a dharma id.
	dh_id text, foreign key(dh_id) references people_main(dh_id)
);

-- For the catalog display
create table if not exists documents(
	name text primary key,
	repo text,
	title json,
	author text,
	editors json,
	langs json,
	summary text,
	foreign key(name) references texts(name)
);

create virtual table if not exists documents_index using fts5(
	name unindexed, -- text primary key references documents(name)
	ident,
	repo,
	title,
	author,
	editor,
	lang,
	summary,
	tokenize = "trigram"
);

-- Language codes and names, extracted from the data table distributed
-- with the relevant standards. We include everything, not just languages
-- used in the project, for simplicity.
create table if not exists langs_list(
	id text primary key check(length(id) = 3),
	name text,
	inverted_name text,
	iso integer check(iso = 3 or iso = 5)
);

create table if not exists langs_by_code(
	code text primary key check(length(code) >= 2 and length(code) <= 3),
	id text, foreign key(id) references langs_list(id)
);

create virtual table if not exists langs_by_name using fts5(
	id unindexed, -- text primary key, foreign key(id) references langs_list(id)
	name,
	tokenize = "trigram"
);

create table if not exists biblio_meta(
	key text primary key not null,
	value
);
insert or ignore into biblio_meta values('latest_version', 0);

create table if not exists biblio_data(
	key text primary key not null,
	version integer not null,
	json json not null check(json_valid(json)),
	short_title as (json ->> '$.data.shortTitle'),
	sort_key blob /* can be null */
);
create index if not exists biblio_data_short_title on biblio_data(short_title);

commit;
