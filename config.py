import os, logging

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

HOST = "0.0.0.0"
PORT = 8023
DEBUG = bool(os.environ.get("DEBUG", False))
DBS_DIR = os.path.join(THIS_DIR, "dbs")
REPOS_DIR = os.path.join(THIS_DIR, "repos")
STATIC_DIR = os.path.join(THIS_DIR, "static")

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL)

with open(os.path.join(THIS_DIR, "version.txt")) as f:
	CODE_HASH = f.read().strip()
