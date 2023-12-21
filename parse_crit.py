def parse_div(p, div):
	p.add_html("<div>")
	type = div["type"]
	if type in ("chapter", "canto", ""):
		p.div_level += 1
		parse_div_section(p, div)
		p.div_level -= 1
	elif type == "dyad":
		parse_div_dyad(p, div)
	elif type == "metrical":
		# Group of verses that share the same meter. Don't exploit this for now.
		assert p.div_level > 1, '<div type="metrical"> can only be used as a child of another <div>'
		p.dispatch_children(div)
	elif type == "interpolation":
		# Ignore for now.
		p.dispatch_children(div)
	else:
		assert 0, div
	p.add_html("</div>")

def parse_div_dyad(p, div):
	for elem in div:
		if elem.type == "tag" and elem.name == "quote":
			assert elem["type"] == "base-text"
			p.add_html('<div class="base-text">')
			p.dispatch_children(elem)
			p.add_html("</div>")
		else:
			p.dispatch(elem)

def parse_div_section(p, div):
	ignore = None
	type = div["type"]
	if type in ("chapter", "canto"):
		p.add_code("log:head<", level=p.div_level)
		p.add_html("<h%d>" % (p.div_level + p.heading_shift))
		p.add_text(type.title())
		n = div["n"]
		if n:
			p.add_text(" %s" % n)
		head = div.find("head")
		if head:
			head = head[0]
			p.add_text(": ")
			parse_div_head(p, head)
			ignore = head
		p.add_html("</h%d>" % (p.div_level + p.heading_shift))
		p.add_code("log:head>")
	elif not type:
		ab = div.find("ab")
		if ab:
			ab = ab[0]
			# Invocation or colophon?
			type = ab["type"]
			assert type in ("invocation", "colophon")
			p.add_code("log:%s<" % ab["type"])
			parse_div_ab(p, ab)
			p.add_code("log:%s>" % ab["type"])
			ignore = ab
	else:
		assert 0, div
	# Render the meter
	if type != "chapter":
		rend = div["rend"]
		assert rend == "met" or not rend
		if rend:
			met = div["met"]
			p.add_html("<h%d>" % (p.div_level + p.heading_shift + 1))
			if met.isalpha():
				pros = prosody.items.get(met)
				assert pros, "meter %r absent from prosodic patterns file" % met
				p.add_code("blank", "%s: %s" % (met.title(), pros))
			p.add_html("</h%d>" % (p.div_level + p.heading_shift + 1))
		else:
			# If we have @met, could use it as a search attribute. Is it often used?
			pass
	else:
		assert not div["rend"]
		assert not div["met"]
	#  Display the contents
	for elem in div:
		if elem == ignore:
			continue
		p.dispatch(elem)

def parse_div_head(p, head):
	def inner(root):
		for elem in root:
			if elem.type == "tag":
				if elem.name == "foreign":
					p.add_html("<i>")
					inner(elem)
					p.add_html("</i>")
				elif elem.name == "hi":
					p.dispatch(elem)
				else:
					assert 0
			else:
				p.dispatch(elem)
	inner(head)

def parse_div_ab(p, ab):
	p.dispatch_children(ab)
