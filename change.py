import os, sys

FIFO_ADDR = "change.hid"

REPOS = """
aditia-phd
arie
arie-corpus
BESTOW
digital-areal
electronic-texts
erc-dharma.github.io
exchange_aurorachana
lexica-indices
mdt-artefacts
mdt-authorities
mdt-editor
mdt-surrogates
mdt-texts
project-documentation
repo-test
siddham
tfa-accalpuram-epigraphy
tfa-cempiyan-mahadevi-epigraphy
tfa-cirkali-epigraphy
tfa-kotumpalur-epigraphy
tfa-melappaluvur-kilappaluvur-epigraphy
tfa-pallava-epigraphy
tfa-pandya-epigraphy
tfa-sii-epigraphy
tfa-tamilnadu-epigraphy
tfa-uttiramerur-epigraphy
tfb-arakan-epigraphy
tfb-badamicalukya-epigraphy
tfb-bengalcharters-epigraphy
tfb-bengalded-epigraphy
tfb-bhaumakara-epigraphy
tfb-daksinakosala-epigraphy
tfb-ec-epigraphy
tfb-eiad-epigraphy
tfb-gangaeast-epigraphy
tfb-kalyanacalukya-epigraphy
tfb-licchavi-epigraphy
tfb-maitraka-epigraphy
tfb-rastrakuta-epigraphy
tfb-sailodbhava-epigraphy
tfb-satavahana-epigraphy
tfb-somavamsin-epigraphy
tfb-telugu-epigraphy
tfb-vengicalukya-epigraphy
tfb-visnukundin-epigraphy
tfc-campa-epigraphy
tfc-khmer-epigraphy
tfc-nusantara-epigraphy
tfd-nusantara-philology
tfd-sanskrit-philology
""".strip().split()

def update_repo(name):
	subprocess.run(["git", "-C",  f"repos/{name}", "pull"], check=True)

def handle(name):
	print(name)

def read_changes(fd):
	buf = ""
	while True:
		data = os.read(fd, 1024)
		if not data:
			break
		buf += data.decode("ascii")
	names = set(buf.splitlines())
	if "ALL" in names:
		handle("ALL")
		return
	for name in names:
		if not name in REPOS:
			print("junk %r" % name, file=sys.stderr)
			continue
		handle(name)

def main():
	try:
		os.unlink(FIFO_ADDR)
	except FileNotFoundError:
		pass
	os.mkfifo(FIFO_ADDR)
	while True:
		fd = os.open(FIFO_ADDR, os.O_RDONLY)
		try:
			read_changes(fd)
		finally:
			os.close(fd)

if __name__ == "__main__":
	main()
