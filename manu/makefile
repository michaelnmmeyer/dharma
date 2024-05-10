corpus.html: corpus.odt parse.py makefile
	pandoc $< -t html4 | nfc | python parse.py > $@
