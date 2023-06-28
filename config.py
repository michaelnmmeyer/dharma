import os

this_dir = os.path.dirname(os.path.abspath(__file__))
in_production = os.getenv("HOST") == "beta"

HOST = "localhost"
PORT = 8023
DEBUG = True
DBS_DIR = os.path.join(this_dir, "dbs")
REPOS_DIR = os.path.join(this_dir, "repos")

if in_production:
	DEBUG = False
	DBS_DIR = "/home/michael/dharma.git/dbs"
	REPOS_DIR = "/home/michael/dharma.git/repos"
