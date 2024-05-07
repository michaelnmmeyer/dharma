import sys
from bs4 import BeautifulSoup

soup = BeautifulSoup(sys.stdin, "html.parser")

for name in ("aside", "a"):
	for tag in soup.find_all(name):
		tag.decompose()
for name in ("blockquote",):
	for tag in soup.find_all(name):
		tag.unwrap()
for name in ("p", "em"):
	for tag in soup.find_all("p"):
		if not tag.get_text():
			tag.decompose()
		elif name == "em" and tag.get_text().isspace():
			tag.unwrap()

print(soup)
