import sys
from dharma import tree

def process(t):
   for node in t.find("//supplied[@reason='omitted']"):
      if node.text() != ",":
         continue
      node["reason"] = "subaudible"

for file in sys.argv[1:]:
   t = tree.parse(file)
   process(t)
   xml = t.xml()
   with open(file, "w") as f:
      f.write(xml)
