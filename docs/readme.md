I have to fix some files, it's not clear how I should proceed viz. who is
responsible for what, who I should tell when I'm modifying file X. And it's not
a good idea to modify the same file at the same time.

For //fileDesc/titleStmt/respStmt/resp, we have many different roles, and there is
also //fileDesc/titleStmt/editor. In the display, we have a single "editor" field,
whatever the file type, and the value of //resp is ignored. I will assume that
everybody mentioned in //titleStmt is an "editor", and treat //resp as free
text, something that should not be normalized. If different roles must be
distinguished, e.g. editor vs. collaborator, I need a clearer notation. The
current one can't be exploited.

    2093 intellectual authorship of edition
    1019 EpiDoc Encoding
     486 Conversion of encoding for DHARMA
     446 EpiDoc encoding
     246 Original EpiDoc Encoding for Siddham
     159 Original EpiDoc Encoding for Siddham, following published edition unless otherwise noted in comments
      70 Encoding
      37 Creation of file
      32 Original EpiDoc Encoding for Siddham, following Ramesh and Tewari's edition unless otherwise noted in comments.
      13 Creation of the file
      13 creation of the file
       7 EpiDoc encoding for DHARMA of parts not yet encoded for Siddham
       5 TEI encoding
       5 structuring of the TEI file
       5 Encoding template for inscription
       3 intellectual authorship of the edition (re-reading)
       2 editorial basis for the re-reading by N. Lakshminarayab Rao
       2 Conversion of encoding with the template V3
       1 Typing of the Sanskrit parts
       1 Typing of the Old Javanese parts (2020–2021)
       1 Typing of the Old Javanese parts (2020)
       1 Structuring of the TEI file and quality control
       1 Photos
       1 Intellectual authorship of the edition
       1 Intellectual authorship of edition
       1 intellectual authorship of apparatus and translation
       1 General supervision and quality control
       1 Encoding of the translation
       1 Encoding of the file
       1 encoding of the edition
       1 editorial suggestion
       1 editorial basis for the re-reading by N. Lakshminarayan Rao
       1 diplomatic edition of the codex unicus
       1 diplomatic edition of a part of the manuscript
       1 creation of file
       1 Chloé

Generally speaking, it's necessary to make a clear distinction between
constrained values and free text, and to be explicit about it so people know
what to do.

For //authority, we have:

    2103 DHARMA
      49 École française d'Extrême-Orient (EFEO)
       9 DHARMA This project has received funding from the European Research Council (ERC) under the European Union's Horizon 2020 research and innovation programme (grant agreement no 809994).
