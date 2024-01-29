-- I initially stored git's commit history in the db, but it made things
-- more complicated for not much benefit, so now only the latest commit
-- is kept. It could be useful to store revisions for Zotero, however,
-- because apparently the online service does not do that (to be
-- confirmed), but this is not done, and likewise it is not really worth
-- the effort, especially for a bibliography.
--
-- It might be useful at some point to use fossil
-- (https://fossil-scm.org/home/dir?ci=tip), which is based on sqlite,
-- if this would allow us to fetch updates faster than with git or more
-- reliably.

begin;

create table if not exists metadata(
	key text primary key,
	value blob
);
-- 'last_updated' is a timestamp updated after each transaction in change.py.
-- The value is only meant for display.
insert or ignore into metadata values('last_updated', 0);
-- All records in biblio_data have a version <= 'biblio_latest_version'. So
-- for updating the biblio we need to fetch all records for which
-- version > 'biblio_latest_version'.
insert or ignore into metadata values('biblio_latest_version', 0);

-- Latest commit of each repo.
create table if not exists commits(
	repo text primary key,
	commit_hash text check(length(commit_hash) = 2 * 20),
	commit_date timestamp
);

-- We store raw xml files in the db. The point is to make it possible to use
-- the main db read-only, without having to clone repos somewhere. Not
-- implemented for now, though. We want to store both texts and other xml
-- files we need to render them (prosody, members).
--
-- The repo name is needed only in the commits table and in the files table.
-- We reproduce it in other tables only to be able to easily delete everything
-- related to a repo when updating the db. XXX we don't do this anymore!
create table if not exists files(
	name text unique,
	repo text,
	path text,
	-- Value of st_mtime. This is not the last time the file was modified
	-- in git. We only use it to figure out which files changed after a
	-- git pull, it is not meant to be displayed.
	mtime timestamp,
	-- When the file was last modified according to git.
	last_modified timestamp,
	data text,
	primary key(name, repo),
	foreign key(repo) references commits(repo)
	-- The file is at https://github.com/erc-dharma/$repo/blob/master/$path
	-- Download link at https://raw.githubusercontent.com/erc-dharma/$repo/master/$path
	-- XXX use a single func somewhere for building url, we are not dealing with e.g.
	-- spaces for now.
);

create table if not exists texts(
	name text primary key,
	repo text,
	html_path text check(html_path is null or length(html_path) > 1),
	code_hash text check(length(code_hash) = 2 * 20),
	-- See the enum in change.py
	status integer check(status >= 0 and status <= 3),
	foreign key(name, repo) references files(name, repo)
	-- The HTML display is at https://erc-dharma.github.io/$repo/$html_path
);

-- For each file, names of the people who modified it at some point in time,
-- so generally multiple "owners" per file.
create table if not exists owners(
	name text,
	git_name text,
	primary key(name, git_name),
	foreign key(name) references files(name)
);
create index if not exists owners_index on owners(git_name);

-- All people mentioned in XML files, both DHARMA people and people
-- outside the project, including historical figures.
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
	-- All the following can be null.
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

-- For the catalog display.
create table if not exists documents(
	name text primary key,
	repo text,
	title json check(json_type(title) = 'array'),
	author text,
	editors json check(json_type(editors) = 'array'),
	langs json check(json_type(langs) = 'array'),
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
	-- Principal language code
	id text primary key check(length(id) >= 3),
	-- Old Cham
	name text,
	-- Cham, Old
	inverted_name text,
	iso integer check(iso is null or iso = 3 or iso = 5),
	custom boolean
);

-- A single language can have several codes.
create table if not exists langs_by_code(
	code text primary key,
	id text, foreign key(id) references langs_list(id)
);

create virtual table if not exists langs_by_name using fts5(
	id unindexed, -- text primary key, foreign key(id) references langs_list(id)
	name,
	tokenize = "trigram"
);

create table if not exists prosody(
	name text primary key not null,
	pattern text not null
);

-- All bibliographic records from Zotero.
create table if not exists biblio_data(
	key text primary key not null,
	version integer not null,
	json json not null check(json_valid(json)),
	-- We don't need to store the short_title, both because it is fast to extract
	-- and because we have an index on it which stores it anyway.
	short_title text as (json ->> '$.data.shortTitle'),
	item_type text as (json ->> '$.data.itemType'),
	-- Null if this is not an entry we can display viz. if it is not of the
	-- item types we support (book, etc.)
	sort_key blob
);
create index if not exists biblio_data_short_title on biblio_data(short_title);
create index if not exists biblio_data_sort_key on biblio_data(sort_key);

commit;
