import os, time, sys
from urllib.parse import urlparse, parse_qs, urlencode
import flask # pip install flask
import requests # pip install requests
from dharma import config

app = flask.Flask(__name__)

def copy_response(r):
	ret = flask.Response(r.text)
	v = r.headers.get("Content-Type")
	if v:
		ret.headers["Content-Type"] = v
	return ret

def next_request_delay(r):
	wait = -1
	n = r.headers.get("Backoff", "")
	if n.isdigit():
		wait = max(wait, int(n))
	n = r.headers.get("Retry-After", "")
	if n.isdigit():
		wait = max(wait, int(n))
	return wait

MY_API_KEY = "ojTBU4SxEQ4L0OqUhFVyImjq"

def do_reply(url):
	url = url._replace(scheme="https", netloc="api.zotero.org")
	url = url.geturl()
	s = requests.Session()
	s.headers["Zotero-API-Version"] = "3"
	s.headers["Zotero-API-Key"] = MY_API_KEY
	for i in range(5):
		r = s.get(url)
		if r.ok:
			return copy_response(r)
		wait = next_request_delay(r)
		# Must be noted that zotero servers return 500 and no request
		# delay when the server is overloaded, thus we retry several
		# times even if no request delay is given.
		if wait <= 0:
			wait = 5
		time.sleep(wait)
	raise Exception(repr((r.headers, r.text)))

@app.get("/groups/1633743/items")
def reply():
	url = urlparse(flask.request.url)
	return do_reply(url)

@app.get("/extra")
@config.transaction("texts")
def by_short_title():
	short_title = flask.request.args["shortTitle"]
	db = config.db("texts")
	(key,) = db.execute("select key from biblio_data where short_title = ?",
		(short_title,)).fetchone() or (None,)
	url = urlparse(flask.request.url)
	params = parse_qs(url.query)
	del params["shortTitle"]
	assert not params.get("itemKey")
	if key:
		params["itemKey"] = key
	else:
		params["tag"] = "zpefiuhzçéé This won't match é)ç'çxhqaàçè-à)"
	params = urlencode(params, doseq=True)
	url = url._replace(path="/groups/1633743/items", query=params)
	print(url.geturl(), file=sys.stderr)
	return do_reply(url)

if __name__ == "__main__":
	app.run(host="localhost", port=8024, debug=True)
