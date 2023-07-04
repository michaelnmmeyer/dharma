from bs4 import BeautifulSoup
from glob import iglob
from dharma.transform import normalize_space

for file in sorted(iglob("texts/*.xml")):
	soup = BeautifulSoup(open(file), "xml")
	for tag in soup.fileDesc.titleStmt.find_all("editor"):
		print(file,normalize_space(tag.get_text().strip()))
