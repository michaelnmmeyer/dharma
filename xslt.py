import sys, saxonche

if __name__ == "__main__":
	proc = saxonche.PySaxonProcessor(license=False)
	xproc = proc.new_xslt30_processor()
	exec = xproc.compile_stylesheet(stylesheet_file=sys.argv[1])
	ret = exec.transform_to_string(source_file=sys.argv[2])
	sys.stdout.write(ret)
