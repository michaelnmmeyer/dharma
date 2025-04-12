from dharma import tree

def to_physical(t):
	for node in t.find("//span[@class='corr' and @standalone='false']"):
		node.delete()
	for node in t.find("//span[@class='reg' and @standalone='false']"):
		node.delete()
	for node in t.find("//ex"):
		node.delete()

def to_logical(t):
	for node in t.find("//span[@class='sic' and @standalone='false']"):
		node.delete()
	for node in t.find("//span[@class='orig' and @standalone='false']"):
		node.delete()
	for node in t.find("//am"):
		node.delete()

def to_full(t):
	for node in t.find("//"):
		pass
