import sys
from bs4 import BeautifulSoup

soup = BeautifulSoup(sys.stdin, "html.parser")

for name in ("aside", "a"):
	for tag in soup.find_all(name):
		tag.decompose()

print(soup)
