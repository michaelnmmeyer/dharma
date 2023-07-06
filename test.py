from bs4 import BeautifulSoup
from glob import iglob
from dharma.transform import normalize_space

critical = sorted(iglob("texts/DHARMA_CritEd*"))
critical_edition = [f for f in critical if not "_trans" in f]
critical_translation = [f for f in critical if "_trans" in f]

for file in sorted(critical_edition):
	soup = BeautifulSoup(open(file), "xml")
	for tag in soup.find_all("div"):
		if not tag.attrs.get("type"):
			print(tag)
			print("---")
