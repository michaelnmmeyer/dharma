all: santi.xml texts

santi.xml: santi.odt
	unzip -p $^ content.xml > $@

texts:
	python3 proc.py
	for f in texts/*.xml; do \
		xmlformat $$f > tmp && mv tmp $$f; \
	done

.PHONY: all texts
