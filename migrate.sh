sqlite dbs/texts.sqlite <<< "
drop table if exists scripts_list;
drop table if exists scripts_by_code;
drop table if exists documents;
drop table if exists documents_index;
"
sqlite dbs/texts.sqlite < schema.sql

