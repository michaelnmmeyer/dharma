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
-- We can fit the whole db into primary memory for now. Allocate 4 GiB.
pragma mmap_size = 4294967296;

create table if not exists critical_cache(
	name text primary key check(typeof(name) = 'text' and length(name) > 0),
	file_hash text check(typeof(file_hash) = 'text'
		and length(file_hash) = 2 * 20),
	code_commit text check(typeof(code_commit) = 'text'
		and length(code_commit) = 2 * 20),
	page html check(typeof(page) = 'text')
);
