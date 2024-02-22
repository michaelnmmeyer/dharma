src = $(wildcard texts/*.txt)
out = $(patsubst %.txt,xml/DHARMA_INSCEC%.xml,$(notdir $(src)))

all: $(out)

xml/DHARMA_INSCEC%.xml: texts/%.txt parse.py tpl.xml
	python parse.py $^
