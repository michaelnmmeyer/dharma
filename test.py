from bs4 import BeautifulSoup
from glob import iglob
from dharma.transform import normalize_space

all = sorted(iglob("texts/DHARMA_*"))
critical = sorted(iglob("texts/DHARMA_CritEd*"))
critical_edition = [f for f in critical if not "_trans" in f]
critical_translation = [f for f in critical if "_trans" in f]
inscriptions = [f for f in all if "DHARMA_INS" in f]

LANGS = """
ara
ban
cja
cjm
deu
eng
fra
ind
jav
jpn
kan
kaw
khm
mya
ndl
obr
ocm
okz
omx
omy
ori
osn
pli
pyx
san
sas
tam
tel
tgl
und
vie
xhm
zlm
""".strip().split() + """
kan-Latn
kaw-Latn
khm-Latn
ocm-Latn
okz-Latn
omy-Latn
ori-Latn
osn-Latn
pli-Latn
pli-Thai
pra-Latn
san-Latn
san-Thai
tam-Latn
tam-Taml
tel-Latn
tha-Thai
xhm-Latn
""".strip().split()

for file in sorted(inscriptions):
	soup = BeautifulSoup(open(file), "xml")
	for tag in soup.find_all(**{"xml:lang": True}):
		print(tag["xml:lang"])
