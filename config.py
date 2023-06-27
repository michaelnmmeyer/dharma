import os

this_dir = os.path.dirname(os.path.abspath(__file__))
in_production = os.getenv("HOST") == "beta"

HOST = "localhost"
PORT = 8023
DEBUG = True
DB_DIR = this_dir
REPOS_DIR = "repos" 

if in_production:
	DEBUG = False
	DB_DIR = "/home/michael/dharma.db"
	REPOS_DIR = "/home/michael/dharma.repos"
