import os, sys
import spacy, stanza
from dharma import tree, langs, common

nlp = spacy.load("en_core_web_sm")
nlp2 = stanza.Pipeline('en', dir='/home/michael/.stanza_resources.tmp')

def process_file(t):
	for trans in t.find("//div[@type='translation']"):
		if trans.assigned_lang.id == "eng":
			break
	else:
		return
	for node in trans.find("//note"):
		node.delete()
	text = trans.text()

	"""
	doc = nlp(text)
	for entity in doc.ents:
		if entity.label_ in ("CARDINAL", "DATE", "ORDINAL"):
			continue
		print(entity.label_, entity.text, sep="\t")
	"""
	doc = nlp2(text)
	for entity in doc.entities:
		print(entity.type, entity.text, sep="\t")
		sys.stdout.flush()




@common.transaction("texts")
def main():
	for file in sys.argv[1:]:
		print(file, file=sys.stderr)
		try:
			t = tree.parse(file)
		except tree.Error:
			continue
		langs.assign_languages(t)
		process_file(t)

main()
