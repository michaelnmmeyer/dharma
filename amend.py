import sys
from dharma import tree

def process(t):
   for node in t.find("//num"):
      if not node.plain:
         continue
      elems = node.text().strip().split()
      sep = ""
      parts = node.copy()
      parts.clear()
      for elem in elems:
         if sep:
            parts.append(sep)
         sep = " "
         if elem.isdigit() and len(elem) in (1, 3, 4):
            parts.append(elem)
         else:
            tag = tree.Tag("g", type="numeral")
            tag.append(elem)
            parts.append(tag)
      node.replace_with(parts)
      #print(node.xml(), parts.xml(), sep="\t")

for file in sys.argv[1:]:
   t = tree.parse(file)
   process(t)
   xml = t.xml()
   with open(file, "w") as f:
      f.write(xml)
