'XSLT transforms'

# Saxon's API doc is here:
# https://www.saxonica.com/saxon-c/doc12/html/saxonc.html
# Experiments show that some objects cannot be shared between threads, and that
# funny things happen when objects that likely reference others go out of scope,
# so we just allocate one processor for each thread, and keep the thing alive
# until the thread exits.

import sys, argparse, threading
import saxonche # pip install saxonche

class Processor:

	def __init__(self):
		self.saxon_proc = saxonche.PySaxonProcessor(license=False)
		self.xslt_proc = self.saxon_proc.new_xslt30_processor()
		self.stylesheets = {}

	def transform(self, xslt_path, text):
		script = self.stylesheets.get(xslt_path)
		if not script:
			script = self.xslt_proc.compile_stylesheet(stylesheet_file=xslt_path)
			self.stylesheets[xslt_path] = script
		# Saxon does not want to find an initial BOM, complains about contents
		# not being allowed in prolog.
		if text.startswith("\N{BOM}"):
			text = text[1:]
		# PyXslt30Processor.transform_to_string(source_file=path) is buggy.
		# When the filename contains space characters, it returns None. So we
		# need to read the file manually and to use
		# transform_to_string(xdm_node=doc) instead, which does work.
		doc = self.saxon_proc.parse_xml(xml_text=text)
		ret = script.transform_to_string(xdm_node=doc)
		assert ret is not None
		return ret

local = threading.local()

def transform(xslt_path, text):
	proc = getattr(local, "processor", None)
	if not proc:
		proc = Processor()
		local.processor = proc
	return proc.transform(xslt_path, text)

if __name__ == "__main__":
	# It is faster to use the python bindings than the Java code for ad hoc
	# transforms, due to Java slow startup time.
	parser = argparse.ArgumentParser()
	parser.add_argument("stylesheet")
	parser.add_argument("input_file", nargs="?")
	args = parser.parse_args()
	if args.input_file:
		with open(args.input_file) as f:
			text = f.read()
	else:
		text = sys.stdin.read()
	ret = transform(args.stylesheet, text)
	sys.stdout.write(ret)
