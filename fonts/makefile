# For building fonts, install fonttools, for pyftsubset.

input_fonts = $(wildcard selection/*.ttf)
output_fonts = $(patsubst %.ttf,%.woff2,$(input_fonts))

all: $(output_fonts) fonts.css

clean:
	$(RM) $(output_fonts) fonts.css unicodes.txt charset.txt unidata/Blocks.txt all_text.txt

.PHONY: all clean

unidata/%.txt:
	curl https://unicode.org/Public/UNIDATA/$(notdir $@) > $@

%.woff2: %.ttf unicodes.txt
	pyftsubset $< --unicodes-file=unicodes.txt --flavor=woff2 --output-file=$@

fonts.css: subset.py $(output_fonts)
	python3 $< $@

unicodes.txt: subset.py charset.txt unidata/Blocks.txt
	python3 $< $@

charset.txt: subset.py all_text.txt
	python3 $< $@

all_text.txt: ../dbs/texts.sqlite ../dbs/biblio.sqlite
	sqlite3 ../dbs/texts.sqlite "select * from files" > $@
	sqlite3 ../dbs/biblio.sqlite "select * from bibliography" >> $@
