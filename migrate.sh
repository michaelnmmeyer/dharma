sqlite dbs/texts.sqlite <<< "
drop table if exists biblio_data;
drop index if exists biblio_data_short_title;
drop index if exists biblio_data_sort_key;
drop view if exists biblio_by_tag;
drop view if exists biblio_authors;
drop table if exists prosody;
"

python biblio.py < repos/bibliography/data.jsonl
python prosody.py
