import sys, requests, bs4

for line in sys.stdin:
	line = line.rstrip()
	if not line:
		continue
	assert line == line.strip()
	elem = line
	attrs = []
	for line in sys.stdin:
		line = line.rstrip()
		if not line:
			break
		assert line.startswith("\t\t")
		attr = line.strip()
		attrs.append(attr)
	module = None
	r = requests.get("https://tei-c.org/release/doc/tei-p5-doc/en/html/ref-%s.html" % elem)
	r.encoding="utf-8"
	soup = bs4.BeautifulSoup(r.text, "html.parser")
	for span in soup.find_all("span", class_="label"):
		if span.string == "Module":
			x = span.parent.next_sibling.next_sibling.get_text()
			module = x.strip().split("—")[0].strip()
			break
	assert module
	print('<elementSpec ident="%s" module="%s" mode="change">' % (elem, module))
	print('    <attList>')
	for attr in attrs:
		print('        <attDef ident="%s" mode="delete"/>' % attr)
	print('    </attList>')
	print('</elementSpec>')

