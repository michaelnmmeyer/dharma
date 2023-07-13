from bs4 import BeautifulSoup
from glob import iglob
from dharma.transform import normalize_space

all = sorted(iglob("texts/DHARMA_*"))
critical = sorted(iglob("texts/DHARMA_CritEd*"))
critical_edition = [f for f in critical if not "_trans" in f]
critical_translation = [f for f in critical if "_trans" in f]
inscriptions = [f for f in all if "DHARMA_INS" in f]

fs = """
texts/DHARMA_INSVengiCalukya00015.xml
texts/DHARMA_INSVengiCalukya00034.xml
texts/DHARMA_INSVengiCalukya00046.xml
""".strip().split()
for file in sorted(fs):
	print("---")
	soup = BeautifulSoup(open(file), "xml")
	for tag in soup.find_all("note"):
		if tag.find("note"):
			print(tag)
