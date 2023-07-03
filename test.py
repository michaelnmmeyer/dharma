from bs4 import BeautifulSoup
from glob import iglob

for file in sorted(iglob("texts/*.xml")):
	soup = BeautifulSoup(open(file), "xml")
	for tag in soup.find_all("authority"):
		print(tag.get_text().strip())
