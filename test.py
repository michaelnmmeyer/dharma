from bs4 import BeautifulSoup
from glob import iglob

for file in sorted(iglob("texts/*.xml")):
	soup = BeautifulSoup(open(file), "xml")
	for tag in soup.find_all("editor"):
		print(file,tag.attrs,tag.get_text().strip().splitlines())
