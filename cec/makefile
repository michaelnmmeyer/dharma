src = $(wildcard tex/*.txt)
out = $(patsubst %.txt,xml/DHARMA_INSCEC%.xml,$(notdir $(src)))

all: $(out)

xml/DHARMA_INSCEC%.xml: tex/%.txt parse.py tpl.xml
	python parse.py $^
