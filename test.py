from glob import iglob
import sys
from dharma import tree, langs

files = sorted(f for f in iglob("texts/DHARMA_INS*") if not "DHARMA_INSEC" in f)

for f in files:
	try:
		t = tree.parse(f)
	except tree.Error:
		continue
	for node in t.find("//*[@rendition]"):
		klass, maturity = [x.split(":", 1)[1] for x in node["rendition"].split()]
		script = langs.get_script(klass)
		maturity = langs.get_script_maturity(maturity)
		#if script.name == "Southern class Brāhmī":
		#	print(f)
		print(maturity.name)

"""

    864 Tamil
    767 Khmer
    635 Grantha
    544 Southern class Brāhmī
     99 Cam
     58 Vaṭṭeḻuttu
     52 Kawi
     13 Kannada
      5 Brāhmī and derivatives
      3 Undetermined
      1 Telugu
      1 Southeast Asian Brāhmī

   1580 Vernacular Brāhmī-derived script
    644 Null
    554 Late Brāhmī
    257 Regional Brāhmī-derived script
      7 Middle Brāhmī


22*5 = 110 total categories

"""
