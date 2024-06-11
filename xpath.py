import argparse, sys
from dharma import common, tree, langs

@common.transaction("texts")
def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("expression")
	parser.add_argument("file", nargs="*")
	args = parser.parse_args()
	f = tree.generator.compile(args.expression)
	if not args.file:
		sys.stdout.write(f.source_code)
		return
	for file in args.file:
		try:
			t = tree.parse(file)
			langs.assign_languages(t)
		except tree.Error:
			continue
		for result in f(t):
			print(f"{tree.term_color('#9d40b4')}>>> {file}{tree.term_color()}")
			print(result.xml())
			sys.stdout.flush()

if __name__ == "__main__":
	try:
		main()
	except (KeyboardInterrupt, BrokenPipeError):
		exit(1)
