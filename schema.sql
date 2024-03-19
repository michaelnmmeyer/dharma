-- I initially stored git's commit history in the db, but it made things
-- more complicated for not much benefit, so now only the latest commit
-- is kept. It could be useful to store revisions for Zotero, however,
-- because apparently the online service does not do that (to be
-- confirmed), but this is not done, and it does not seem worth
-- the effort, especially for a bibliography.
--
-- It might be useful at some point to use fossil
-- (https://fossil-scm.org/home/dir?ci=tip), which is based on sqlite,
-- if this would allow us to fetch updates faster than with git, or more
-- reliably.

pragma page_size = 16384;
pragma journal_mode = wal;
pragma synchronous = normal;
pragma foreign_keys = on;
pragma secure_delete = off;

begin;

create table if not exists metadata(
	key text primary key,
	value blob
);
-- 'last_updated' is a timestamp updated after each transaction in change.py.
-- The value is only meant for display.
insert or ignore into metadata values('last_updated', 0);
-- To update the bibliography, we need to pull all zotero items whose version
-- is > biblio_latest_version. We might already have such items in the db if
-- a request to the Zotero API failed.
insert or ignore into metadata values('biblio_latest_version', 0);

-- Repositories description. This is filled with repos.tsv. We do not attempt
-- to update repos that do not appear there, even if these repos are cloned
-- into repos/. XXX should trigger a clone-or-pull when this is changed.
create table if not exists repos(
	repo text primary key check(length(repo) > 0),
	-- Whether contains or might contain edited texts (texts that we can
	-- display in the catalog), per contrast with repos that just include
	-- metadata or other stuff.
	textual boolean check(textual = 0 or textual = 1),
	title text check(length(title) > 0)
);

-- Latest commit of each repo we keep track of. XXX what if not yet cloned?
create table if not exists commits(
	repo text primary key,
	commit_hash text check(length(commit_hash) = 2 * 20),
	commit_date timestamp,
	foreign key(repo) references repos(repo)
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
	last_modified_commit text check(length(last_modified_commit) = 2 * 20),
	data text, -- XXX this should be a blob, because we parse XML as byte strings anyway and
	-- because we probably also will store binary files
	-- The following are stored because format_url is an external function and
	-- because we want to be able to check this field from the sqlite command-line
	-- tool.
	-- XXX don't use external functions like that, prevents us from creating
	-- the db outside of python.
	github_view_url text as (format_url('https://github.com/erc-dharma/%s/blob/master/%s', repo, path)) stored,
	github_raw_url text as (format_url('https://raw.githubusercontent.com/erc-dharma/%s/master/%s', repo, path)) stored,
	primary key(name, repo),
	foreign key(repo) references commits(repo)
);

create table if not exists texts(
	name text primary key,
	repo text,
	html_path text check(html_path is null or length(html_path) > 1),
	code_hash text check(length(code_hash) = 2 * 20),
	-- See the enum in change.py
	status integer check(status >= 0 and status <= 3),
	html_url text as (format_url('https://erc-dharma.github.io/%s/%s', repo, html_path)) stored,
	foreign key(name, repo) references files(name, repo)
);

-- For each file, git names of the people who modified it at some point in time.
-- We thus often have multiple "owners" per file.
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

-- This is filled with the git names data file. To dump a list of all
-- contributors:
-- for repo in repos/*; do git -C $repo log --format=%aN; done | sort -u
-- XXX Apparently there is no internal git ids or something to identify
-- Maybe we should use the tuple (user.name,user.email) as key, or just
-- user.email? Problem with user.email is that github assigns generated emails.
create table if not exists people_github(
	git_name text primary key not null,
	-- Might be null, not all people on github have a dharma id.
	dh_id text,
	foreign key(dh_id) references people_main(dh_id)
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
	name unindexed, -- references documents(name)
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
-- with the relevant standards and with the DHARMA-specific language table.
-- We include everything, not just languages used in the project, for
-- simplicity.
create table if not exists langs_list(
	-- Principal language code
	id text primary key check(length(id) >= 3),
	-- Old Cham
	name text,
	-- Cham, Old
	inverted_name text,
	-- "iso" is null when the language code is a custom one viz. a
	-- DHARMA-specific one.
	iso integer check(iso is null or iso = 3 or iso = 5),
	custom boolean
);

-- A single language can have several codes.
create table if not exists langs_by_code(
	code text primary key,
	id text,
	foreign key(id) references langs_list(id)
);

create virtual table if not exists langs_by_name using fts5(
	id unindexed, -- references langs_list(id)
	name,
	tokenize = "trigram"
);

create table if not exists prosody(
	name text primary key not null,
	pattern text not null
);

create table if not exists gaiji(
	name text primary key not null,
	text text,
	description text
);

-- All bibliographic records from Zotero. Includes data that we do not care
-- about.
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
