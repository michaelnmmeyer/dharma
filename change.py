import os, sys, subprocess

from dharma import config

FIFO_ADDR = os.path.join(config.REPOS_DIR, "change.hid")

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

def command(*cmd):
	print(*cmd, file=sys.stderr)
	subprocess.run(cmd, check=True)

def update_repo(name):
	command("git", "-C",  os.path.join(config.REPOS_DIR, name), "pull")

def clone_all():
	for name in REPOS:
		command("git", "clone", f"git@github.com:erc-dharma/{name}.git", f"repos/{name}")

def read_changes(fd):
	buf = ""
	while True:
		data = os.read(fd, 1024)
		if not data:
			break
		buf += data.decode("ascii")
	names = set(buf.splitlines())
	if "all" in names:
		names = REPOS
	for name in names:
		if not name in REPOS:
			print("junk repo name: %r" % name, file=sys.stderr)
			continue
		print(f"updating {name}", file=sys.stderr)
		update_repo(name)

def main():
	if not os.path.exists("repos"):
		os.mkdir("repos")
		clone_all()
	try:
		os.mkfifo(FIFO_ADDR)
	except FileExistsError:
		pass
	while True:
		fd = os.open(FIFO_ADDR, os.O_RDONLY)
		try:
			read_changes(fd)
		finally:
			os.close(fd)

# To be used by the client
def notify(name):
	try:
		os.mkfifo(FIFO_ADDR)
	except FileExistsError:
		pass
	fd = os.open(FIFO_ADDR, os.O_RDWR | os.O_NONBLOCK)
	try:
		os.write(fd, name.encode("ascii") + b"\n")
	finally:
		os.close(fd)

if __name__ == "__main__":
	main()
