-- We initially stored git's commit history in the db, but it made things
-- more complicated for not much benefit, so now only the latest commit
-- is kept. It could be useful to store revisions for Zotero, however,
-- because apparently the online service does not do that (to be
-- confirmed), but this is not done, and it does not seem worth
-- the effort, especially for a bibliography.
--
-- It might be useful at some point to use fossil
-- (https://fossil-scm.org/home/dir?ci=tip), which is based on sqlite, if this
-- would allow us to fetch updates faster than with git or to execute history
-- commands faster.

pragma page_size = 16384;
pragma journal_mode = wal;
-- According to the doc (https://www.sqlite.org/pragma.html#pragma_synchronous),
-- dbs in wal mode are safe with synchronous = normal. In fact we do not really
-- care if the db gets corrupted as it can be reconstrued easily, so even
-- synchronous = off might be OK.
pragma synchronous = normal;
pragma foreign_keys = on;
-- secure_delete is enabled per default on some platforms. We do not manage
-- sensible data, so the overhead is uneeded.
pragma secure_delete = off;

begin;

create table if not exists metadata(
	key text primary key,
	value blob
);
-- 'last_updated' is a timestamp updated after each write transaction.
-- The value is only meant for display.
insert or ignore into metadata values('last_updated', 0);
-- To update the bibliography, we need to pull from zotero.org all records
-- whose version is > biblio_latest_version. We might already have such items in
-- the db.
insert or ignore into metadata values('biblio_latest_version', 0);

-- Repositories description. This is initially filled with repos.tsv. We do
-- not attempt to update repos that do not appear there, even if these repos are
-- cloned into repos/.
create table if not exists repos(
	-- Repository name, e.g. tfa-pallava-epigraphy
	repo text primary key check(length(repo) > 0),
	-- Whether this repository contains or might contain edited texts
	-- (texts that we can display in the catalog), per contrast with repos
	-- that include other kinds of stuff (metadata, plain text, etc.). We
	-- use this to avoid processing repositories that do not contain data
	-- useful for the app.
	textual boolean check(textual = 0 or textual = 1) default true,
	-- User-readable name for the repository. Displayed on the website.
	title text check(title != ''),
	-- Latest commit in this repo.
	commit_hash text check(commit_hash is null or length(commit_hash) = 2 * 20),
	commit_date timestamp check(commit_date is null or typeof(commit_date) = 'integer'),
	-- Commit hash of the python code that was used for processing this
	-- repository. We need to process it again if the python code has been
	-- updated in the meantime.
	code_hash text check(code_hash is null or length(code_hash) = 2 * 20)
);

-- We need this to trigger the first update in change.py
insert or ignore into repos(repo) values('project-documentation');

-- We store the raw contents of all the files we process in the db.
--
-- We do this because it is necessary for preserving transactions' semantics.
-- If we try to read files from the file system in the server code, we will at
-- some point read files that are being modified with a git pull from change.py.
-- To prevent this from happening, all main processes except the change process
-- should only access files from the db itself, never from the file system.
--
-- There is also another motivation: ultimately, we want the app to be able to
-- run read-only, on a personal computer, without having to clone repos
-- somewhere and without accessing external services. This is not implemented
-- for now, though.
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
	-- git pull, it is not meant to be displayed. We could also store a
	-- hash of the file, to be able to tell which files actually changed,
	-- but this seems unnecessary for now.
	mtime timestamp,
	-- When the file was last modified according to git. This is only used
	-- for display.
	last_modified timestamp,
	last_modified_commit text check(length(last_modified_commit) = 2 * 20),
	-- Raw data, might not be valid UTF-8.
	data blob,
	-- To view the file on github:
	-- https://github.com/erc-dharma/$repo/blob/master/$path
	-- To view the raw file on github:
	-- https://raw.githubusercontent.com/erc-dharma/$repo/master/$path
	primary key(name, repo),
	foreign key(repo) references repos(repo)
);

-- For each file, git names of the people who modified it at some point in time.
-- We thus often have multiple "owners" per file. In any case, we should have at
-- least one owner per file.
create table if not exists owners(
	name text check(length(name) > 0),
	git_name text check(length(git_name) > 0),
	primary key(name, git_name),
	foreign key(name) references files(name)
);
create index if not exists owners_index on owners(git_name);

-- All DHARMA people who have a DHARMA id, and only them.
create table if not exists people_main(
	dh_id text primary key check(length(dh_id) = 4),
	-- Two forms: ["Emmanuel", "Francis"] or ["Tyassanti Kusumo Dewanti"]
	name json check(
		json_array_length(name) between 1 and 2
		and json_type(name -> 0) = 'text'
		and json_array_length(name) = 1 or json_type(name -> 1) = 'text'),
	-- e.g. "Emmanuel Francis" or "Tyassanti Kusumo Dewanti"
	print_name text as (iif(json_array_length(name) = 1,
		name ->> 0,
		printf('%s %s', name ->> 0, name ->> 1))),
	-- e.g. "Francis, Emmanuel" or "Tyassanti Kusumo Dewanti"
	inverted_name text as (iif(json_array_length(name) = 1,
		name ->> 0,
		printf('%s, %s', name ->> 1, name ->> 0))),
	-- All the following can be null.
	affiliation text check(affiliation != ''),
	idhal text unique check(idhal != ''),
	idref text unique check(idref != ''),
	orcid text unique check(orcid != ''),
	viaf text unique check(viaf != ''),
	wikidata text unique check(wikidata != '')
);

-- This is filled with the git names data file. To dump a list of all
-- contributors:
-- for repo in repos/*; do git -C $repo log --format="%aN|%aE"; done | sort -u | while IFS='|' read -r name; do grep "^$name"$'\t' repos/project-documentation/DHARMA_gitNames.tsv || echo "$name"; done
-- TODO Apparently there is no internal git ids or something to identify
-- Maybe we should use the tuple (user.name,user.email) as key, or just
-- user.email? Problem with user.email is that github assigns generated emails.
create table if not exists people_github(
	git_name text primary key check(length(git_name) > 0),
	dh_id text,
	foreign key(dh_id) references people_main(dh_id)
);

-- All texts, parsed.
create table if not exists documents(
	name text primary key,
	repo text,
	title text check(title is null or title != ''),
	author text check(author is null or author != ''),
	editors json check(json_type(editors) = 'array'),
	-- Dharma members ids viz. the xxxx in part:xxxx.
	editors_ids json check(json_type(editors_ids) = 'array'),
	langs json check(json_type(langs) = 'array'),
	summary text,
	-- The corresponding file is at https://erc-dharma.github.io/$repo/$html_path
	html_path text check(html_path is null or length(html_path) > 1),
	-- See the enum in change.py
	status integer check(status >= 0 and status <= 3),
	foreign key(name, repo) references files(name, repo)
);

-- Inverted index for the catalog display. We have exactly one row for each text
-- in the documents table.
create virtual table if not exists documents_index using fts5(
	name unindexed, -- references documents(name)
	ident,
	repo,
	title,
	author,
	editor,
	editor_id,
	lang,
	summary,
	tokenize = "trigram"
);

-- Language codes and names, extracted from the data table distributed
-- with the relevant standards and from the dharma-specific language table
-- stored in project-documentation. We include everything, not just languages
-- used in the project, to allow people to use new language codes if need be.
create table if not exists langs_list(
	-- Principal language code. If this is an ISO code, it is always of
	-- length 3. Longer language codes are used for custom dharma-specific
	-- languages.
	id text primary key check(length(id) >= 3),
	-- E.g. "Old Cham"
	name text check(length(name) > 0),
	-- E.g. "Cham, Old". Used for sorting.
	inverted_name text check(length(name) > 0),
	-- "iso" is null when the language code is a custom one viz. a
	-- dharma-specific one.
	iso integer check(iso is null or iso = 3 or iso = 5),
	-- custom is true if we have modified the default name and
	-- inverted_name values present in the ISO standard, or if the language
	-- code is a DHARMA-specific one.
	custom boolean,
	-- dharma is true if the language appears in the DHARMA languages list
	dharma boolean,
	check(length(id) = 3 and iso is not null
		or length(id) > 3 and iso is null and custom)
);

-- A single language can have several codes.
create table if not exists langs_by_code(
	-- Length two or three for ISO codes, length > 3 for custom DHARMA
	-- codes.
	code text primary key check(length(code) >= 2),
	id text,
	foreign key(id) references langs_list(id)
);

-- Inverted index for searching languages by full name.
create virtual table if not exists langs_by_name using fts5(
	id unindexed, -- references langs_list(id)
	name,
	tokenize = "trigram"
);

create view if not exists langs_prod as
	select json_each.value as lang,
		count(*) as lang_prod
	from documents join json_each(documents.langs)
	group by lang;

create view if not exists langs_editors_prod as
	select langs_iter.value as lang,
		editor_iter.value as editor,
		count(*) as editor_prod
	from documents
		join json_each(documents.langs) as langs_iter
		join json_each(documents.editors_ids) as editor_iter
	group by lang, editor
	order by lang, editor_prod desc;

create view if not exists langs_repos_prod as
	select langs_iter.value as lang,
		repo,
		count(*) as repo_prod
	from documents
		join json_each(documents.langs) as langs_iter
	group by lang, repo
	order by lang, repo_prod desc;

create view if not exists langs_display as
	with langs_editors_prod_json as (
		select lang,
			json_group_array(json_array(dh_id, print_name, editor_prod))
				as editors
		from langs_editors_prod
			join people_main on langs_editors_prod.editor = people_main.dh_id
		group by lang
		order by editor_prod desc, inverted_name
	), langs_repos_prod_json as (
		select lang,
			json_group_array(json_array(repo, repo_prod)) as repos
		from langs_repos_prod
		group by lang
	)
	select
		langs_list.id as lang,
		langs_list.name as name,
		langs_prod.lang_prod as prod,
		editors,
		repos,
		case iso
			when null then 'DHARMA-specific'
			else case custom
				when true then printf('ISO 639-%d (modified)', iso)
				else printf('ISO 639-%d', iso)
			end
		end as standard
	from langs_list
		join langs_prod
			on langs_list.id = langs_prod.lang
		join langs_editors_prod_json
			on langs_list.id = langs_editors_prod_json.lang
		join langs_repos_prod_json
			on langs_list.id = langs_repos_prod_json.lang
	order by langs_list.inverted_name;

create table if not exists prosody(
	name text primary key check(length(name) > 0),
	pattern text check(length(pattern) > 0)
);

create table if not exists gaiji(
	name text primary key check(length(name) > 0),
	text text check(text is null or length(text) > 0),
	description text check(description is null or length(description) > 0)
);

-- All bibliographic records from Zotero. Includes data that we do not care
-- about e.g. attachments records.
create table if not exists biblio_data(
	key text primary key check(length(key) > 0),
	-- We expect version numbers to be > 0, otherwise the update code is
	-- broken.
	version integer check(version > 0),
	-- Full record we get from the Zotero API.
	json json not null check(json_valid(json)),
	-- We don't need to store the short_title, both because it is fast to
	-- extract and because we have an index on it which stores it anyway.
	short_title text as (case json ->> '$.data.shortTitle'
		when '' then null
		else json ->> '$.data.shortTitle'
		end),
	item_type text as (json ->> '$.data.itemType')
		check(item_type is not null),
	-- Null if this is not an entry we can display viz. if it is not of the
	-- item types we support (book, etc.).
	sort_key text collate icu
);
create index if not exists biblio_data_short_title on biblio_data(short_title);
create index if not exists biblio_data_sort_key on biblio_data(sort_key);

create view if not exists biblio_by_tag as
	select json_each.value ->> '$.tag' as tag, biblio_data.key as key
	from biblio_data join json_each(biblio_data.json -> '$.data.tags')
	order by tag;

create view if not exists repos_editors_stats as
	select repo,
		json_each.value as editor_id,
		people_main.print_name as editor,
		count(*) as editor_prod
	from documents
		join json_each(documents.editors_ids)
		join people_main on people_main.dh_id = json_each.value
	group by repo, json_each.value
	order by repo asc, editor_prod desc, people_main.inverted_name asc;

create view if not exists repos_editors_stats_json as
	select repo,
		json_group_array(json_array(editor_id, editor, editor_prod))
			as editors_prod
	from repos_editors_stats group by repo;

create view if not exists repos_langs_stats as
	select repo,
		langs_list.id as lang_id,
		langs_list.name as lang,
		count(*) as lang_prod
	from documents, json_each(documents.langs)
		left join langs_list on langs_list.id = json_each.value
	group by repo, json_each.value
	order by repo asc, lang_prod desc, lang asc;

create view if not exists repos_langs_stats_json as
	select repo,
		json_group_array(json_array(lang_id, lang, lang_prod)) as langs_prod
	from repos_langs_stats group by repo;

create view if not exists repos_display as
	with repos_stats as (
		select repos.repo,
			count(*) as repo_prod
		from repos join documents on repos.repo = documents.repo
		group by repos.repo
		order by repos.repo
	)
	select repos.repo,
		repos.title,
		repo_prod,
		editors_prod as people,
		langs_prod as langs,
		repos.commit_hash,
		repos.commit_date
	from repos
		left join repos_stats on repos.repo = repos_stats.repo
		left join repos_editors_stats_json
			on repos.repo = repos_editors_stats_json.repo
		left join repos_langs_stats_json
			on repos.repo = repos_langs_stats_json.repo
	group by repos.repo
	order by repos.title;

commit;
