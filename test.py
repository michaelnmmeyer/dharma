import sys
from bs4 import BeautifulSoup
from glob import iglob
from dharma.transform import normalize_space

all = sorted(iglob("texts/DHARMA_*"))
inscriptions = [f for f in all if "DHARMA_INS" in f]
critical = sorted(iglob("texts/DHARMA_CritEd*"))
critical_edition = [f for f in critical if not "_trans" in f]
critical_translation = [f for f in critical if "_trans" in f]

chars = set()
for file in sys.stdin:
	file = file.strip()
	chars |= set(open(file).read())
print(chars)

