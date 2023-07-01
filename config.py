import os

this_dir = os.path.dirname(os.path.abspath(__file__))
in_production = os.getenv("HOST") == "beta"

HOST = "0.0.0.0"
PORT = 8023
DEBUG = False
DBS_DIR = os.path.join(this_dir, "dbs")
REPOS_DIR = os.path.join(this_dir, "repos")
